'use strict';
const screen=document.querySelector('#screen'),notice=document.querySelector('#notice');
let user=null;
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function clear(){document.body.classList.remove('conversation-view');document.querySelector('#live-corrections')?.remove();screen.replaceChildren();notice.textContent='';}
function title(text,description){clear();screen.append(el('h2',text));if(description)screen.append(el('p',description,'muted'));}
function button(text,fn,cls){const n=el('button',text,cls);n.type='button';n.addEventListener('click',()=>run(fn,n));return n;}
async function run(fn,b){notice.textContent='';if(b)b.disabled=true;try{await fn();}catch(e){notice.textContent=e.message;}finally{if(b)b.disabled=false;}}
async function api(path,data){let r;try{r=await fetch('/api'+path,{method:data===undefined?'GET':'POST',headers:data===undefined?{}:{'Content-Type':'application/json'},body:data===undefined?undefined:JSON.stringify(data)});}catch{throw Error('Brak połączenia z serwerem. Sprawdź połączenie i odśwież historię przed ponownym wysłaniem.');}const body=await r.json();if(!r.ok){if(r.status===401&&user){user=null;account();authView();}throw Error(typeof body.detail==='string'?body.detail:'Nie udało się wykonać operacji.');}return body;}
function field(form,label,name,type='text'){const id='field-'+name,l=el('label',label),i=el('input');l.htmlFor=id;i.id=id;i.name=name;i.type=type;i.required=true;if(type==='password'){i.minLength=10;i.maxLength=128;i.autocomplete='new-password';}if(type==='email')i.autocomplete='email';form.append(l,i);return i;}
function submit(form,text,fn){const b=el('button',text);b.type='submit';form.append(b);form.addEventListener('submit',e=>{e.preventDefault();run(fn,b);});}
function account(){const n=document.querySelector('#account');n.replaceChildren();if(user)n.append(el('span',user.email),button('Wyloguj',async()=>{await api('/auth/logout',{});user=null;account();authView();},'secondary'));}
function authView(mode='login',token=''){title(mode==='register'?'Utwórz konto':mode==='forgot'?'Przypomnij hasło':mode==='reset'?'Ustaw nowe hasło':'Witaj ponownie',mode==='login'?'Zaloguj się i wróć do nauki.':'Hasło powinno mieć od 10 do 128 znaków.');const f=el('form');screen.append(f);const email=mode==='reset'?null:field(f,'E-mail','email','email');const password=mode==='forgot'?null:field(f,'Hasło','password','password');if(mode==='login')password.autocomplete='current-password';submit(f,mode==='login'?'Zaloguj się':mode==='register'?'Zarejestruj się':mode==='forgot'?'Wyślij instrukcję':'Zapisz hasło',async()=>{const body=mode==='forgot'?{email:email.value}:mode==='reset'?{token,password:password.value}:{email:email.value,password:password.value};const r=await api('/auth/'+mode,body);if(mode==='login'){user=await api('/auth/me');account();await setup();}else{authView();notice.textContent=r.message;}});const links=el('div',undefined,'links');for(const [label,m] of mode==='login'?[['Zapomniałem hasła','forgot'],['Utwórz konto','register']]:[['Wróć do logowania','login']]){const a=el('a',label);a.href='#';a.onclick=e=>{e.preventDefault();authView(m);};links.append(a);}screen.append(links);}
function choice(label,values,selected){const l=el('label',label),s=el('select');s.id='select-'+label;l.htmlFor=s.id;for(const [value,text] of values){const o=el('option',text);o.value=value;s.append(o);}s.value=selected;screen.append(l,s);return s;}
let selectedLanguage='EN',selectedLevel='A1',conversation=null;
async function setup(){title('Ustawienia rozmowy','Wybierz język i poziom, na którym chcesz ćwiczyć.');const lang=choice('Język',[['PL','Polski'],['EN','Angielski'],['ES','Hiszpański']],selectedLanguage),level=choice('Poziom CEFR',['A1','A2','B1','B2','C1','C2'].map(x=>[x,x]),selectedLevel);lang.onchange=()=>selectedLanguage=lang.value;level.onchange=()=>selectedLevel=level.value;const row=el('div',undefined,'row');row.append(button('Rozpocznij',async()=>{const c=await api('/conversations',{language:lang.value,level:level.value});await chat(c.id);}),button('Historia rozmów',historyView,'secondary'),button('Statystyki',()=>statsView(lang.value),'secondary'));screen.append(row);const active=await api('/conversations');for(const c of active){const p=el('p');p.append(button('Wznów rozmowę · '+c.language+' / '+c.level,()=>chat(c.id),'secondary'));screen.append(p);}}
async function chat(id){
 conversation=await api('/conversations/'+id);
 title('Twoja rozmowa','Pisz w wybranym języku. Korekty znajdziesz obok rozmowy.');
 document.body.classList.add('conversation-view');
 screen.append(el('span',conversation.language+' · '+conversation.level,'badge'));
 const history=transcript(conversation.messages,'Zacznij od przywitania lub opowiedz o swoim dniu.');
 screen.append(history);history.scrollTop=history.scrollHeight;
 const f=el('form'),label=el('label','Napisz wiadomość…'),text=el('textarea');
 text.maxLength=4000;text.required=true;text.id='message';label.htmlFor='message';f.append(label,text);
 submit(f,'Wyślij',async()=>{
  try{await api('/conversations/'+id+'/messages',{text:text.value});}
  catch(e){await chat(id);throw e;}
  await chat(id);document.querySelector('#message').focus();
 });
 screen.append(f);
 const actions=el('div',undefined,'row');
 actions.append(button('Zakończ rozmowę',async()=>{await api('/conversations/'+id+'/finish',{});await results(id);},'secondary'));
 screen.append(actions);
 liveCorrections(conversation);
}

function transcript(messages,empty){
 const history=el('div',undefined,'chat');history.setAttribute('role','log');
 if(!messages.length)history.append(el('p',empty,'muted'));
 for(const m of messages){
  const b=el('div',undefined,'bubble '+m.author);
  b.append(el('strong',m.author==='user'?'Ty':'AI'),document.createTextNode(m.text));
  if(m.author==='user'&&m.status!=='evaluated')b.append(el('small','Wiadomość nieoceniona.'));
  history.append(b);
 }
 return history;
}

function date(ts){return new Date(ts*1000).toLocaleString('pl-PL',{dateStyle:'medium',timeStyle:'short'});}

async function historyView(){
 const items=await api('/conversations/history');
 title('Historia rozmów','Zakończone rozmowy. Otwórz rozmowę, aby przeczytać ją ponownie, przejrzeć korekty lub ją kontynuować.');
 if(!items.length)screen.append(el('p','Nie masz jeszcze zakończonych rozmów.','muted'));
 const list=el('ul',undefined,'history');
 for(const c of items){
  const li=el('li'),info=el('div');
  info.append(el('b',c.language+' · '+c.level),el('small',date(c.end_ts)+' · wiadomości: '+c.user_messages+' · błędy: '+c.error_count));
  li.append(info,button('Otwórz',()=>results(c.id),'secondary'));
  list.append(li);
 }
 screen.append(list);
 const row=el('div',undefined,'row');row.append(button('Wróć',setup,'secondary'));screen.append(row);
}

function liveCorrections(data){
 const panel=el('aside',undefined,'panel corrections-panel');panel.id='live-corrections';
 panel.setAttribute('aria-labelledby','corrections-title');panel.setAttribute('aria-live','polite');
 const heading=el('h2','Korekty na bieżąco');heading.id='corrections-title';
 panel.append(heading,el('p','Zdania, poprawki i wyjaśnienia z tej rozmowy.','muted'));
 if(data.errors.length){
  const list=el('ol',undefined,'errors');
  for(const error of data.errors){
   const item=el('li');
   item.append(el('p',error.sentence),el('p','→ '+error.correction,'correction'),el('small',error.description));
   list.append(item);
  }
  panel.append(list);
 }else{
  const assessed=data.messages.some(m=>m.author==='user'&&m.status==='evaluated');
  panel.append(el('p',assessed?'Nie wykryto błędów w ocenionych wiadomościach.':'Korekty pojawią się tutaj po ocenie Twojej wiadomości.','corrections-empty'));
 }
 if(data.messages.some(m=>m.author==='user'&&m.status!=='evaluated'))panel.append(el('p','Wiadomości bez oceny nie mają jeszcze korekt.','muted'));
 notice.before(panel);
}
async function results(id){const data=await api('/conversations/'+id+'/summary');title('Błędy w rozmowie','Przeczytaj korekty i wykorzystaj je w następnej rozmowie.');screen.append(el('span',data.conversation.language+' · '+data.conversation.level,'badge'));if(data.unassessed_messages)screen.append(el('p','Wiadomości bez oceny: '+data.unassessed_messages+'. Nie wliczono ich zdań do ocen.','muted'));if(!data.errors.length)screen.append(el('p','Nie wykryto błędów w ocenionych wiadomościach.'));const list=el('ol',undefined,'errors');for(const e of data.errors){const li=el('li');li.append(el('p',e.sentence),el('p','→ '+e.correction,'correction'),el('small',e.description));list.append(li);}screen.append(list);metrics(data.stats);const log=el('details',undefined,'transcript');log.append(el('summary','Przebieg rozmowy ('+data.messages.length+' wiadomości)'),transcript(data.messages,'Ta rozmowa nie zawiera wiadomości.'));screen.append(log);const actions=el('div',undefined,'row');actions.append(button('Kontynuuj rozmowę',async()=>{await api('/conversations/'+id+'/resume',{});await chat(id);}),button('Nowa rozmowa',setup,'secondary'),button('Historia rozmów',historyView,'secondary'),button('Statystyki',()=>statsView(data.conversation.language),'secondary'));screen.append(actions);}
async function init(){const token=new URLSearchParams(location.search).get('reset');if(token){history.replaceState(null,'','/');authView('reset',token);return;}try{user=await api('/auth/me');account();await setup();}catch{authView();}}
function metrics(data){const grid=el('div',undefined,'metrics');for(const [value,label] of [[data.error_percent.toLocaleString('pl-PL',{maximumFractionDigits:1})+'%','Błędne zdania'],[data.words_per_minute.toLocaleString('pl-PL',{maximumFractionDigits:1}),'Słów na minutę'],[data.words_spoken,'Słowa wypowiedziane'],[data.unique_words,'Unikalne słowa']]){const cell=el('div',undefined,'metric');cell.append(el('b',String(value)),el('span',label));grid.append(cell);}screen.append(grid,el('p','Zdania poprawne: '+data.correct_sentences+' · błędne: '+data.incorrect_sentences+' · nieocenione: '+data.unassessed_sentences,'muted'));if(!data.assessed_sentences)screen.append(el('p','Brak ocenionych zdań — procent błędów nie jest jeszcze miarodajny.','muted'));if(data.duration_seconds===0)screen.append(el('p','Brak czasu rozmowy — tempo wynosi 0 słów/min.','muted'));}
async function statsView(language=selectedLanguage){const data=await api('/stats/'+language);title('Twoje statystyki','Wyniki zakończonych rozmów od ostatniego resetu.');const lang=choice('Język',[['PL','Polski'],['EN','Angielski'],['ES','Hiszpański']],language);lang.onchange=()=>run(()=>statsView(lang.value));metrics(data);const row=el('div',undefined,'row');row.append(button('Nowa rozmowa',setup,'secondary'),button('Resetuj statystyki',async()=>{if(!confirm('Wyzerować statystyki języka '+language+'? Rozmowy i korekty pozostaną zapisane.'))return;await api('/stats/'+language+'/reset',{});await statsView(language);},'danger'));screen.append(row);}
init();


