// Orthogonal native UML routing; no Mermaid parser or Mermaid renderer.
const fs=require('fs'),path=require('path'),os=require('os');
const ELK=require(process.env.RP4_ELK_MODULE||path.join(os.tmpdir(),'rp4-complete-class-20261020/node_modules/elkjs/lib/elk.bundled.js'));
const [input,output]=process.argv.slice(2);
(async()=>{
 const elk=new ELK();const graphs=JSON.parse(fs.readFileSync(input,'utf8')),result=[];
 for(const graph of graphs){
  const r=await elk.layout(graph);result.push(r);
 }
 fs.writeFileSync(output,JSON.stringify(result));
})().catch(e=>{console.error(e);process.exit(1)});
