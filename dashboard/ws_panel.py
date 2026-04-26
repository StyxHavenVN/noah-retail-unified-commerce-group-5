"""
Real-Time WebSocket Panel for Streamlit Dashboard.
Generates an HTML component with Socket.IO that connects to
the WebSocket server and shows live order notifications.
"""

WS_REALTIME_HTML = """
<div id="ws-panel" style="background:rgba(0,210,255,0.06);border:1px solid rgba(0,210,255,0.15);border-radius:14px;padding:1rem 1.5rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
  <div style="display:flex;align-items:center;gap:0.8rem;">
    <span id="ws-dot" style="width:10px;height:10px;border-radius:50%;background:#ff9100;display:inline-block;animation:blink 1.5s infinite;"></span>
    <span style="color:#ccc;font-size:0.85rem;font-weight:600;">&#x1F4E1; Real-Time Hub</span>
    <span id="ws-txt" style="color:rgba(255,255,255,0.4);font-size:0.8rem;">&#x23F3; Connecting...</span>
  </div>
  <div style="display:flex;align-items:center;gap:1.5rem;">
    <div style="text-align:center;">
      <div id="live-cnt" style="font-size:1.6rem;font-weight:800;color:#00d2ff;transition:all 0.3s;">0</div>
      <div style="color:rgba(255,255,255,0.4);font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;">New Orders (Live)</div>
    </div>
    <div id="last-ord" style="background:rgba(255,255,255,0.05);padding:0.4rem 0.8rem;border-radius:8px;font-size:0.8rem;color:rgba(255,255,255,0.5);min-width:150px;">Waiting for orders...</div>
  </div>
</div>
<style>
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.3}}
@keyframes pulse{0%{transform:scale(1);color:#00d2ff}50%{transform:scale(1.3);color:#00e676}100%{transform:scale(1);color:#00d2ff}}
.flash{animation:pulse 0.5s ease-in-out;}
</style>
<script src="https://cdn.socket.io/4.7.4/socket.io.min.js"></script>
<script>
(function(){
  var c=0;
  var s=io('http://localhost:5002',{transports:['websocket','polling'],reconnection:true,reconnectionDelay:2000});
  s.on('connect',function(){
    var d=document.getElementById('ws-dot');
    var t=document.getElementById('ws-txt');
    if(d){d.style.background='#00e676';d.style.animation='none';}
    if(t)t.textContent='Connected \\u2713';
  });
  s.on('disconnect',function(){
    var d=document.getElementById('ws-dot');
    var t=document.getElementById('ws-txt');
    if(d){d.style.background='#ff4757';d.style.animation='blink 1s infinite';}
    if(t)t.textContent='Disconnected...';
  });
  s.on('new_order',function(data){
    c++;
    var el=document.getElementById('live-cnt');
    if(el){el.textContent=c;el.classList.remove('flash');void el.offsetWidth;el.classList.add('flash');}
    var l=document.getElementById('last-ord');
    if(l){l.style.color='#00e676';l.innerHTML='\\ud83c\\udd95 Order #'+data.order_id+' \\u2014 User '+data.user_id;setTimeout(function(){l.style.color='rgba(255,255,255,0.5)';},2000);}
    var p=document.getElementById('ws-panel');
    if(p){p.style.borderColor='rgba(0,230,118,0.5)';setTimeout(function(){p.style.borderColor='rgba(0,210,255,0.15)';},1000);}
  });
  s.on('connect_error',function(){
    var t=document.getElementById('ws-txt');
    if(t)t.textContent='WS Error';
  });
})();
</script>
"""
