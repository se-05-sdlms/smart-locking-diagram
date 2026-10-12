# Architecture Diagram

```mermaid
flowchart TD

    %% =========================
    %% CLIENT LAYER
    %% =========================
    subgraph Clients["🖥️ Client Layer"]
        direction LR
        A["📱 Resident Mobile App"]
        B["🚚 Shipper Guest Web<br/>Mobile Web"]
        C["🧑‍🔧 Locker Operator Web"]
        D["🧑‍💼 Administrator Web"]
    end


    %% =========================
    %% BACKEND LAYER
    %% =========================
    subgraph Backend["⚙️ ASP.NET Core Backend"]
        P["Presentation Layer<br/>REST API · Swagger · SignalR"]
        AP["Application Layer<br/>Use Cases · Interfaces · Validation"]
        DM["Domain Layer<br/>Entities · Value Objects · Business Rules"]
        I["Infrastructure Layer<br/>EF Core · External Services · MQTT"]

        P --> AP
        AP --> DM
        AP --> I
    end


    %% =========================
    %% DATA & INFRASTRUCTURE
    %% =========================
    DB[("🗄️ PostgreSQL Database<br/>Supabase")]
    CS["☁️ Cloud Storage<br/>Waybill / Incident Images"]
    E["📡 EMQX MQTT Broker<br/>MQTT v5.0"]


    %% =========================
    %% EXTERNAL SERVICES
    %% =========================
    PAY["💳 Payment Gateway"]
    NOTI["🔔 Notification Services<br/>Push · SMS · Email"]
    OCR["🔎 OCR Service"]


    %% =========================
    %% LOCKER HARDWARE
    %% =========================
    subgraph Locker["🔐 Smart Locker"]
        F["🔌 ESP32 Locker Controller<br/>ESP32 WROOM 32D"]
        G["🔒 Locker Hardware<br/>Electronic Lock · Relay · Door Sensor"]
        F -->|"Control and read status"| G
    end


    %% =========================
    %% CLIENT → BACKEND
    %% =========================
    A -->|"(1) HTTPS / REST API / JWT<br/>SignalR Realtime"| P
    B -->|"(1) HTTPS / REST API / Guest Session"| P
    C -->|"(1) HTTPS / REST API / JWT<br/>SignalR Realtime"| P
    D -->|"(1) HTTPS / REST API / JWT"| P


    %% =========================
    %% BACKEND → DATA / SERVICES
    %% =========================
    I <-->|"(2) Entity Framework Core"| DB
    I <-->|"(3) Upload / Retrieve Media"| CS
    I <-->|"(4) Payment Request / Webhook"| PAY
    I -->|"(5) Push / SMS / Email"| NOTI
    I <-->|"(6) OCR Request / OCR Result"| OCR
    I <-->|"(7) MQTT Publish / Subscribe"| E


    %% =========================
    %% MQTT → LOCKER
    %% =========================
    E <-->|"(8) MQTT over Wi-Fi / Internet"| F


    %% =========================
    %% BLUETOOTH DIRECT PATH
    %% =========================
    A <-.->|"(9) Bluetooth Direct Unlock"| F


    %% =========================
    %% STYLES
    %% =========================
    style P fill:#dbeafe,stroke:#2563eb,stroke-width:2px
    style AP fill:#ede9fe,stroke:#7c3aed,stroke-width:2px
    style DM fill:#fef3c7,stroke:#d97706,stroke-width:2px
    style I fill:#dcfce7,stroke:#16a34a,stroke-width:2px

    style DB fill:#f3e8ff,stroke:#9333ea,stroke-width:2px
    style CS fill:#e0f2fe,stroke:#0284c7,stroke-width:2px
    style E fill:#ccfbf1,stroke:#0f766e,stroke-width:2px

    style PAY fill:#fce7f3,stroke:#db2777,stroke-width:2px
    style NOTI fill:#fef9c3,stroke:#ca8a04,stroke-width:2px
    style OCR fill:#ecfccb,stroke:#65a30d,stroke-width:2px

    style F fill:#ffedd5,stroke:#ea580c,stroke-width:2px
    style G fill:#fee2e2,stroke:#dc2626,stroke-width:2px

    style A fill:#eff6ff,stroke:#3b82f6
    style B fill:#eff6ff,stroke:#3b82f6
    style C fill:#eff6ff,stroke:#3b82f6
    style D fill:#eff6ff,stroke:#3b82f6
```

---

## Guidelines & Standards

- Xem quy chuẩn và hướng dẫn vẽ Class Diagram (Mermaid tương thích Draw.io) tại: [CLASS_DIAGRAM_GUIDELINES.md](CLASS_DIAGRAM_GUIDELINES.md)
- Xem quy chuẩn và hướng dẫn vẽ Sequence Diagram (Mermaid tương thích Draw.io) tại: [SEQUENCE_DIAGRAM_GUIDELINES.md](SEQUENCE_DIAGRAM_GUIDELINES.md)
