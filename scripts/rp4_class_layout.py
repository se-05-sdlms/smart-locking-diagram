"""Readable five-column UML layout with obstacle-aware orthogonal routing.

The class content comes from the backend model. This module only decides where
boxes and connectors go. Every connector gets an independent port and route so
draw.io does not stack relationship lines or multiplicity labels.
"""

from __future__ import annotations

from collections import defaultdict
from heapq import heappop, heappush


GRID = 8
BOX_GAP = 64
COLUMN_GAP = 144
ROUTE_CLEARANCE = 16
PORT_ESCAPE = 24


def _snap(value):
    return int(round(value / GRID) * GRID)


def _ordered_columns(model):
    nodes = model['nodes']
    by_name = {n['name']: n for n in nodes}
    dtos = sorted(
        (n for n in nodes if n['role'] == 'DTO'),
        key=lambda n: (0 if n['name'].endswith(('Request', 'Payload')) else 1, n['name']))
    controllers = sorted(
        (n for n in nodes if n['role'] in ('controller', 'worker')),
        key=lambda n: (0 if n['role'] == 'controller' else 1, n['name']))
    services = [n for n in nodes if n['role'] == 'service']
    interfaces = [n for n in nodes if n['role'] == 'interface']

    primary_service = None
    primary_interface = None
    for service in services:
        implemented = next((name for name in service.get('implements', []) if name in by_name), None)
        if implemented:
            primary_service, primary_interface = service, by_name[implemented]
            break
    if primary_service is None and services:
        primary_service = services[0]
    if primary_interface is None and interfaces:
        primary_interface = interfaces[0]

    primary = [n for n in (primary_interface, primary_service) if n is not None]
    remaining = [n for n in nodes if n['role'] in ('interface', 'service', 'persistence') and n not in primary]
    auxiliary = []
    for interface in sorted((n for n in remaining if n['role'] == 'interface'), key=lambda n: n['name']):
        auxiliary.append(interface)
        auxiliary.extend(sorted(
            (n for n in remaining if n['role'] == 'service' and interface['name'] in n.get('implements', [])),
            key=lambda n: n['name']))
    auxiliary.extend(sorted((n for n in remaining if n not in auxiliary and n['role'] == 'service'), key=lambda n: n['name']))
    auxiliary.extend(sorted((n for n in remaining if n['role'] == 'persistence'), key=lambda n: n['name']))
    entities = [n for n in nodes if n['role'] == 'entity']
    return [column for column in (dtos, controllers, primary, auxiliary, entities) if column]


def _place_nodes(model):
    columns = _ordered_columns(model)
    stack_heights = [sum(n['height'] for n in col) + BOX_GAP * (len(col) - 1) for col in columns]
    tallest = max(stack_heights, default=0)
    x = 48
    positions = {}
    for col_index, (column, stack_height) in enumerate(zip(columns, stack_heights)):
        width = max(n['width'] for n in column)
        y = 48 + max(0, (tallest - stack_height) // 2)
        for row, node in enumerate(column):
            positions[node['name']] = {
                'id': node['name'], 'x': _snap(x), 'y': _snap(y),
                'width': node['width'], 'height': node['height'],
                'col': col_index, 'row': row,
            }
            y += node['height'] + BOX_GAP
        x += width + COLUMN_GAP
    width = _snap(max((p['x'] + p['width'] for p in positions.values()), default=1100) + 160)
    height = _snap(max((p['y'] + p['height'] for p in positions.values()), default=600) + 160)

    # The allocation view has three associations from ReturnRequest back to
    # the Locker/LockerCompartment/Reservation chain. Keeping every entity in
    # one vertical column forces all three routes into the same narrow right
    # gutter. Put ReturnRequest in its own entity column so each association
    # has a clear horizontal routing lane and readable endpoint labels.
    if model['key'] == '3.3.1' and 'ReturnRequest' in positions:
        request = positions['ReturnRequest']
        request.update(x=1520, y=376, col=3, row=0)
        width = _snap(max(p['x'] + p['width'] for p in positions.values()) + 160)
        height = _snap(max(p['y'] + p['height'] for p in positions.values()) + 160)

    # Keep the two expiration paths parallel: worker -> contract/service ->
    # shared allocation/persistence -> owner entities. The generic role-based
    # columns split the return pair from the delivery pair and make the
    # persistence line loop around every entity on the right.
    if model['key'] == '3.3.2':
        custom = {
            'DeliveryRequestExpirationWorker': (48, 352, 0, 0),
            'IDeliveryRequestService':          (496, 136, 1, 0),
            'DeliveryRequestService':           (496, 272, 1, 1),
            'IReturnRequestService':            (496, 504, 1, 2),
            'ReturnRequestService':             (496, 640, 1, 3),
            'ICompartmentAllocationService':    (936, 240, 2, 0),
            'ApplicationDbContext':             (936, 456, 2, 1),
            'DeliveryRequest':                  (1376, 80, 3, 0),
            'CompartmentReservation':           (1376, 432, 3, 1),
            'ReturnRequest':                    (1376, 672, 3, 2),
        }
        for name, (node_x, node_y, column, row) in custom.items():
            positions[name].update(x=node_x, y=node_y, col=column, row=row)
        width = _snap(max(p['x'] + p['width'] for p in positions.values()) + 160)
        height = _snap(max(p['y'] + p['height'] for p in positions.values()) + 160)

    # Pickup authorization carries four DTO dependencies plus three persistence
    # targets. Give every layer a wider routing gutter so the accepts/returns
    # and persists labels do not sit on adjacent connector elbows.
    if model['key'] == '3.4.1':
        columns = {
            'ParcelsController': 448,
            'IParcelPickupService': 896,
            'ParcelPickupService': 896,
            'ILockerAccessService': 1360,
            'ParcelRetrievalEligibility': 1360,
            'ApplicationDbContext': 1360,
            'Parcel': 1840,
            'OverdueCharge': 1840,
            'ResidentProfile': 1840,
        }
        for name, node_x in columns.items():
            positions[name]['x'] = node_x
        width = _snap(max(p['x'] + p['width'] for p in positions.values()) + 160)
        height = _snap(max(p['y'] + p['height'] for p in positions.values()) + 160)

    # Separate device-command DTOs and the access-event relationships. With
    # every entity in one column, persistence to Locker detours around the
    # whole entity stack and LockerAccessEvent reuses the same right gutter for
    # both of its associations.
    if model['key'] == '3.4.2':
        custom = {
            'OpenLockerRequest':            (48, 48, 0, 0),
            'BluetoothCommandResponse':     (48, 328, 0, 1),
            'OpenLockerResponse':           (48, 504, 0, 2),
            'ILockerAccessService':         (464, 280, 1, 0),
            'LockerAccessService':          (464, 432, 1, 1),
            'IBluetoothMessageCodec':       (936, 152, 2, 0),
            'ILockerCommandDispatcher':     (936, 328, 2, 1),
            'MqttLockerCommandDispatcher':  (936, 472, 2, 2),
            'ApplicationDbContext':         (936, 640, 2, 3),
            'LockerUnlockCommand':          (1408, 48, 3, 0),
            'Locker':                       (1408, 248, 3, 1),
            'LockerCompartment':            (1408, 456, 3, 2),
            'LockerAccessEvent':            (1848, 456, 4, 0),
        }
        for name, (node_x, node_y, column, row) in custom.items():
            positions[name].update(x=node_x, y=node_y, col=column, row=row)
        width = _snap(max(p['x'] + p['width'] for p in positions.values()) + 160)
        height = _snap(max(p['y'] + p['height'] for p in positions.values()) + 160)

    # Entity-heavy views need two semantic columns. Detail/history entities
    # stay next to the persistence layer because the DbContext references all
    # of them; aggregate owners sit in the outer column.  The result keeps the
    # more numerous persistence dependencies short while giving associations
    # and multiplicities a clear gutter of their own.
    entity_layouts = {
        '3.4.4': {
            'LockerAccessEvent':    (1744, 160, 4, 0),
            'LockerCompartment':    (1744, 360, 4, 1),
            'ParcelStatusHistory':  (1744, 536, 4, 2),
            'Parcel':               (2144, 32, 5, 0),
            'DeliveryRequest':      (2144, 720, 5, 1),
        },
        '3.5.1': {
            'LockerCompartment':    (1744, 160, 4, 0),
            'OperatorAssignment':   (1744, 432, 4, 1),
            'Locker':               (2144, 280, 5, 0),
        },
        '3.7.1': {
            'OverdueCharge':        (1376, 80, 3, 0),
            'SystemPolicy':         (1376, 320, 3, 1),
            'ParcelStatusHistory':  (1376, 624, 3, 2),
            'Parcel':               (1776, 160, 4, 0),
            'DeliveryRequest':      (1776, 400, 4, 1),
        },
        '3.8.4': {
            'OperatorAssignment':   (1744, 80, 4, 0),
            'Locker':               (1744, 288, 4, 1),
            'AuditLog':             (1744, 496, 4, 2),
            'User':                 (2144, 240, 5, 0),
        },
        '3.8.6': {
            'Incident':             (1744, 160, 4, 0),
            'OverdueCharge':        (1744, 400, 4, 1),
            'Locker':               (2144, 160, 5, 0),
            'Parcel':               (2144, 400, 5, 1),
        },
        '3.9.1': {
            'ResidentProfile':      (1744, 120, 4, 0),
            'Locker':               (1744, 400, 4, 1),
            'ReturnRequest':        (2144, 240, 5, 0),
        },
    }
    if model['key'] in entity_layouts:
        for name, (node_x, node_y, column, row) in entity_layouts[model['key']].items():
            positions[name].update(x=node_x, y=node_y, col=column, row=row)
        width = _snap(max(p['x'] + p['width'] for p in positions.values()) + 160)
        height = _snap(max(p['y'] + p['height'] for p in positions.values()) + 160)
    return positions, width, height


def _edge_sides(edge, positions):
    source, target = positions[edge['a']], positions[edge['b']]
    if source['col'] < target['col']:
        return 'right', 'left'
    if source['col'] > target['col']:
        return 'left', 'right'
    if abs(source['row'] - target['row']) > 1:
        return 'right', 'right'
    if source['y'] <= target['y']:
        return 'bottom', 'top'
    return 'top', 'bottom'


def _port_assignments(model, positions):
    groups = defaultdict(list)
    sides = {}
    for index, edge in enumerate(model['edges']):
        source_side, target_side = _edge_sides(edge, positions)
        sides[index] = source_side, target_side
        a, b = positions[edge['a']], positions[edge['b']]
        groups[(edge['a'], source_side)].append((index, b['y'] + b['height'] / 2, b['x'] + b['width'] / 2))
        groups[(edge['b'], target_side)].append((index, a['y'] + a['height'] / 2, a['x'] + a['width'] / 2))

    ports = {}
    for (name, side), entries in groups.items():
        node = positions[name]
        entries.sort(key=lambda item: item[1] if side in ('left', 'right') else item[2])
        count = len(entries)
        for rank, (edge_index, _, __) in enumerate(entries, 1):
            fraction = rank / (count + 1)
            if side == 'left':
                point = (node['x'], _snap(node['y'] + max(18, min(node['height'] - 18, node['height'] * fraction))))
            elif side == 'right':
                point = (node['x'] + node['width'], _snap(node['y'] + max(18, min(node['height'] - 18, node['height'] * fraction))))
            elif side == 'top':
                point = (_snap(node['x'] + max(18, min(node['width'] - 18, node['width'] * fraction))), node['y'])
            else:
                point = (_snap(node['x'] + max(18, min(node['width'] - 18, node['width'] * fraction))), node['y'] + node['height'])
            ports[(edge_index, name)] = point
    return sides, ports


def _escape(point, side):
    x, y = point
    if side == 'left': return x - PORT_ESCAPE, y
    if side == 'right': return x + PORT_ESCAPE, y
    if side == 'top': return x, y - PORT_ESCAPE
    return x, y + PORT_ESCAPE


def _blocked_cells(positions, width, height):
    blocked = set()
    for node in positions.values():
        left = _snap(node['x'] - ROUTE_CLEARANCE)
        right = _snap(node['x'] + node['width'] + ROUTE_CLEARANCE)
        top = _snap(node['y'] - ROUTE_CLEARANCE)
        bottom = _snap(node['y'] + node['height'] + ROUTE_CLEARANCE)
        for x in range(max(0, left), min(width, right) + GRID, GRID):
            for y in range(max(0, top), min(height, bottom) + GRID, GRID):
                blocked.add((x, y))
    return blocked


def _route(start, goal, blocked, width, height, used, used_points):
    start, goal = (_snap(start[0]), _snap(start[1])), (_snap(goal[0]), _snap(goal[1]))
    queue = [(0, 0, start[0], start[1], '')]
    best = {(start[0], start[1], ''): 0}
    previous = {}
    directions = ((GRID, 0, 'h'), (-GRID, 0, 'h'), (0, GRID, 'v'), (0, -GRID, 'v'))
    while queue:
        _, cost, x, y, direction = heappop(queue)
        state = (x, y, direction)
        if cost != best.get(state):
            continue
        if (x, y) == goal:
            path = [(x, y)]
            while state in previous:
                state = previous[state]
                path.append((state[0], state[1]))
            path.reverse()
            simplified = [path[0]]
            for i in range(1, len(path) - 1):
                before, current, after = path[i - 1], path[i], path[i + 1]
                if (current[0] - before[0], current[1] - before[1]) != (after[0] - current[0], after[1] - current[1]):
                    simplified.append(current)
            simplified.append(path[-1])
            return simplified
        for dx, dy, new_direction in directions:
            nx, ny = x + dx, y + dy
            if nx < 16 or ny < 16 or nx > width - 16 or ny > height - 16:
                continue
            if (nx, ny) in blocked and (nx, ny) not in (start, goal):
                continue
            segment = ((min(x, nx), min(y, ny)), (max(x, nx), max(y, ny)))
            reuse = used.get(segment, 0)
            if reuse:
                continue
            other_direction = 'v' if new_direction == 'h' else 'h'
            crossing_penalty = 80 * sum(point in used_points[other_direction] for point in ((x,y),(nx,ny)))
            turn = 0 if not direction or direction == new_direction else 12
            next_cost = cost + 1 + turn + reuse * 28 + crossing_penalty
            next_state = (nx, ny, new_direction)
            if next_cost >= best.get(next_state, 10**12):
                continue
            best[next_state] = next_cost
            previous[next_state] = state
            heuristic = (abs(goal[0] - nx) + abs(goal[1] - ny)) // GRID
            heappush(queue, (next_cost + heuristic, next_cost, nx, ny, new_direction))
    raise RuntimeError(f'No orthogonal route from {start} to {goal}')


def _mark_used(points, used, used_points):
    for a, b in zip(points, points[1:]):
        x, y = a
        dx = 0 if a[0] == b[0] else GRID if b[0] > a[0] else -GRID
        dy = 0 if a[1] == b[1] else GRID if b[1] > a[1] else -GRID
        while (x, y) != b:
            nx = b[0] if dx and abs(b[0] - x) <= GRID else x + dx
            ny = b[1] if dy and abs(b[1] - y) <= GRID else y + dy
            segment = ((min(x, nx), min(y, ny)), (max(x, nx), max(y, ny)))
            used[segment] += 1
            direction='h' if y==ny else 'v'
            used_points[direction].add((x,y));used_points[direction].add((nx,ny))
            x, y = nx, ny


def layout(model):
    positions, width, height = _place_nodes(model)
    sides, ports = _port_assignments(model, positions)
    blocked = _blocked_cells(positions, width, height)
    used = defaultdict(int)
    used_points = {'h':set(),'v':set()}
    used_geometry = []
    routed = [None] * len(model['edges'])

    # Adjacent UML layers have a dedicated empty gutter. Assign every edge in
    # that gutter its own vertical lane instead of letting A* progressively
    # block the short routes and push later DTO dependencies around the page.
    adjacent_groups = defaultdict(list)
    for index, edge in enumerate(model['edges']):
        source, target = positions[edge['a']], positions[edge['b']]
        source_side, target_side = sides[index]
        if abs(source['col'] - target['col']) == 1 and {source_side, target_side} == {'left', 'right'}:
            adjacent_groups[tuple(sorted((source['col'], target['col'])))].append(index)
    adjacent_lanes = {}
    for column_pair, indexes in adjacent_groups.items():
        indexes.sort(key=lambda i: (
            (ports[(i, model['edges'][i]['a'])][1] + ports[(i, model['edges'][i]['b'])][1]) / 2,
            i))
        left_edges=[];right_edges=[]
        for index in indexes:
            edge=model['edges'][index];a=positions[edge['a']];b=positions[edge['b']]
            left,right=(a,b) if a['col']<b['col'] else (b,a)
            left_edges.append(left['x']+left['width']+PORT_ESCAPE)
            right_edges.append(right['x']-PORT_ESCAPE)
        lane_left=max(left_edges);lane_right=min(right_edges)
        if lane_right > lane_left:
            available = list(range(_snap(lane_left), _snap(lane_right) + GRID, GRID))
            available = [x for x in available if lane_left <= x <= lane_right]
            for rank,index in enumerate(indexes,1):
                ideal = lane_left+(lane_right-lane_left)*rank/(len(indexes)+1)
                adjacent_lanes[index]=(available, ideal)
    order = sorted(range(len(model['edges'])), key=lambda i: (
        abs(positions[model['edges'][i]['a']]['col'] - positions[model['edges'][i]['b']]['col']),
        abs(positions[model['edges'][i]['a']]['y'] - positions[model['edges'][i]['b']]['y'])))
    for index in order:
        edge = model['edges'][index]
        source_side, target_side = sides[index]
        source_port = ports[(index, edge['a'])]
        target_port = ports[(index, edge['b'])]
        source, target = positions[edge['a']], positions[edge['b']]
        if (model['key'], edge['a'], edge['b']) == ('3.4.4', 'ApplicationDbContext', 'Parcel'):
            # Parcel sits beyond the detail-entity column.  Use the free upper
            # corridor explicitly; generic A* otherwise adds two tiny jogs at
            # the expanded DbContext obstacle before reaching the same lane.
            track_x = _snap(source_port[0] + 80)
            points = [source_port, (track_x, source_port[1]),
                      (track_x, target_port[1]), target_port]
        elif source['col'] == target['col'] and {source_side, target_side} == {'top', 'bottom'}:
            middle_y = _snap((source_port[1] + target_port[1]) / 2)
            points = [source_port, (source_port[0], middle_y),
                      (target_port[0], middle_y), target_port]
        elif index in adjacent_lanes:
            source_escape = tuple(_snap(v) for v in _escape(source_port, source_side))
            target_escape = tuple(_snap(v) for v in _escape(target_port, target_side))
            available, ideal = adjacent_lanes[index]
            candidates = sorted(available, key=lambda x: (abs(x-ideal), x))
            points = None
            for track_x in candidates:
                candidate = [source_port, source_escape,
                             (track_x, source_escape[1]), (track_x, target_escape[1]),
                             target_escape, target_port]
                compact_candidate = [candidate[0]]
                for point in candidate[1:]:
                    if point == compact_candidate[-1]:
                        continue
                    if len(compact_candidate) >= 2:
                        a, b = compact_candidate[-2], compact_candidate[-1]
                        if (a[0] == b[0] == point[0]) or (a[1] == b[1] == point[1]):
                            compact_candidate[-1] = point
                            continue
                    compact_candidate.append(point)
                overlaps = False
                for a, b in zip(compact_candidate, compact_candidate[1:]):
                    for p, q in used_geometry:
                        horizontal = (a[1] == b[1] == p[1] == q[1] and
                                      max(min(a[0], b[0]), min(p[0], q[0])) <
                                      min(max(a[0], b[0]), max(p[0], q[0])))
                        vertical = (a[0] == b[0] == p[0] == q[0] and
                                    max(min(a[1], b[1]), min(p[1], q[1])) <
                                    min(max(a[1], b[1]), max(p[1], q[1])))
                        if horizontal or vertical:
                            overlaps = True
                            break
                    if overlaps:
                        break
                if not overlaps:
                    points = candidate
                    break
            if points is None:
                middle = _route(source_escape, target_escape, blocked, width, height, used, used_points)
                points = [source_port, source_escape, *middle[1:-1], target_escape, target_port]
        else:
            source_escape = tuple(_snap(v) for v in _escape(source_port, source_side))
            target_escape = tuple(_snap(v) for v in _escape(target_port, target_side))
            middle = _route(source_escape, target_escape, blocked, width, height, used, used_points)
            points = [source_port, source_escape, *middle[1:-1], target_escape, target_port]
        compact = [points[0]]
        for point in points[1:]:
            if point == compact[-1]:
                continue
            if len(compact) >= 2:
                a, b = compact[-2], compact[-1]
                if (a[0] == b[0] == point[0]) or (a[1] == b[1] == point[1]):
                    compact[-1] = point
                    continue
            compact.append(point)
        _mark_used(compact, used, used_points)
        used_geometry.extend(zip(compact, compact[1:]))
        routed[index] = {
            'id': str(index),
            'exitX': (source_port[0] - source['x']) / source['width'],
            'exitY': (source_port[1] - source['y']) / source['height'],
            'entryX': (target_port[0] - target['x']) / target['width'],
            'entryY': (target_port[1] - target['y']) / target['height'],
            'sourceSide': source_side, 'targetSide': target_side,
            'sections': [{'startPoint': dict(x=compact[0][0], y=compact[0][1]),
                          'bendPoints': [dict(x=x, y=y) for x, y in compact[1:-1]],
                          'endPoint': dict(x=compact[-1][0], y=compact[-1][1])}],
        }
    return {'id': model['key'], 'width': width, 'height': height,
            'children': list(positions.values()), 'edges': routed}
