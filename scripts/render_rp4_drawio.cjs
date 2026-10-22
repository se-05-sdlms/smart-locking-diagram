// Render the saved native mxGraph pages themselves, without a Mermaid renderer.
// Dependencies are paths passed by the caller; no package installation or network is needed.
const fs=require('fs'),path=require('path');
const [file,out,puppeteerPath,mxClientPath,shapesPath]=process.argv.slice(2);
if(!shapesPath)throw Error('Usage: node render_rp4_drawio.cjs <drawio> <output> <puppeteer-dir> <mxClient.js> <Shapes.js>');
const puppeteer=require(puppeteerPath);
(async()=>{
 fs.mkdirSync(out,{recursive:true});
 const browser=await puppeteer.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--no-sandbox']});
 const results=[];
 try{
  const page=await browser.newPage();
  await page.setContent('<html><body style="margin:0;background:#f5f5f5"><div id="graph" style="position:relative"></div></body></html>');
  await page.evaluate(()=>{window.mxLoadResources=false;window.mxLoadStylesheets=false;});
  await page.addScriptTag({path:mxClientPath});
  await page.evaluate(()=>{window.Graph=mxGraph;window.urlParams={};window.Editor={};Graph.prototype.convertValueToString=function(cell){return String(cell.value||'');};});
  await page.addScriptTag({path:shapesPath});
  const pages=await page.evaluate(xml=>{
   const doc=new DOMParser().parseFromString(xml,'text/xml');
   if(doc.querySelector('parsererror'))throw Error('Invalid draw.io XML');
   return [...doc.querySelectorAll('diagram')].map(d=>({name:d.getAttribute('name'),key:d.getAttribute('id').replace('rp4-',''),xml:new XMLSerializer().serializeToString(d.firstElementChild)}));
  },fs.readFileSync(file,'utf8'));
  for(const item of pages){
   const r=await page.evaluate(item=>{
    const host=document.getElementById('graph');host.innerHTML='';
    const graph=new Graph(host);graph.setHtmlLabels(true);graph.setEnabled(false);
    const doc=mxUtils.parseXml(item.xml);
    document.body.style.background=doc.documentElement.getAttribute('background')||'#ffffff';
    new mxCodec().decode(doc.documentElement,graph.getModel());graph.refresh();
    const b=graph.getGraphBounds();
    const cells=Object.values(graph.getModel().cells);
    if(cells.length<=2||[...doc.querySelectorAll('mxCell[vertex="1"]')].every(c=>c.getAttribute('umlRole')==='blankImportAnchor'))return {blank:true,cells:cells.length};
    const scale=Math.min(1,1800/(b.x+b.width+48));
    graph.view.setScale(scale);
    const invalid=cells.filter(c=>c.vertex&&graph.view.getState(c)==null).length;
    const clipping=[];
    const classIds=new Set([...doc.querySelectorAll('mxCell[umlRole="classBox"]')].map(c=>c.getAttribute('id')));
    for(const c of cells.filter(c=>classIds.has(c.id))){
     const state=graph.view.getState(c),node=state?.text?.node;
     if(!node)continue;
     const expected={x:state.x,y:state.y,right:state.x+state.width,bottom:state.y+state.height};
     // Inspect actual rendered text ranges, rather than relying on XML box dimensions.
     const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);
     let text;
     while(text=walker.nextNode()){
      if(!text.textContent.trim())continue;
      const range=document.createRange();range.selectNodeContents(text);
      for(const b of range.getClientRects())if(b.left<expected.x-2||b.top<expected.y-2||b.right>expected.right+2||b.bottom>expected.bottom+2){clipping.push(c.id);break;}
     }
    }
    window.previewGraph=graph;
    return {width:Math.ceil((b.x+b.width+48)*scale),height:Math.ceil((b.y+b.height+48)*scale),cells:cells.length,invalid,clippedClassBoxes:[...new Set(clipping)]};
   },item);
   if(!r.blank){
    await page.setViewport({width:Math.max(100,r.width),height:Math.max(100,r.height),deviceScaleFactor:1});
    await page.screenshot({path:path.join(out,item.key+'.png')});
   }
   results.push({key:item.key,...r});
  }
  fs.writeFileSync(path.join(out,'render-check.json'),JSON.stringify(results,null,2));
  console.log(JSON.stringify({pages:results.length,rendered:results.filter(r=>!r.blank).length,blank:results.filter(r=>r.blank).length,invalid:results.reduce((n,r)=>n+(r.invalid||0),0)}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
