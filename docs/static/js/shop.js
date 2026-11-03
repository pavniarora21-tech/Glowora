document.querySelectorAll('.chip').forEach(function(c){c.addEventListener('click',function(){
 document.querySelectorAll('.chip').forEach(function(x){x.classList.remove('on')});c.classList.add('on');
 var k=c.dataset.cat;document.querySelectorAll('.card[data-cat]').forEach(function(p){p.style.display=(!k||p.dataset.cat===k)?'':'none'});});});
