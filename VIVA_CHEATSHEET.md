# Viva Cheat Sheet — Saylani Student Ops Desk

Simple words hain, jargon nahi. Har cheez English + Roman Urdu dono mein.
Kal ye file khol kar padh lena — 15-20 minute lagenge poori padhne mein.

---

## 1. Project Ek Line Mein Kya Hai?

**English:** A chatbot for bootcamp students. It answers questions about courses,
assignments, and careers — using real data, never guessing — and always ends with
a structured record (a "Ticket"), not just plain text.

**Roman Urdu:** Ye ek chatbot hai bootcamp students ke liye. Ye courses, assignments,
aur career ke sawalon ka jawab deta hai — real data se, kabhi guess nahi karta —
aur hamesha ek structured "Ticket" (form jaisi cheez) bana kar khatam karta hai,
sirf simple text nahi.

---

## 2. File-by-File — Kya Hai, Kyun Hai, Kya Problem Solve Karta Hai

### 📋 Spec Files (code likhne se pehle banayi gayi)

**`constitution.md`**
- **Kya hai:** Rules ki list jo kabhi toot nahi sakti — jaise "secrets sirf `.env` mein rahen", "koi bhi tool crash nahi karega".
- **Kyun hai:** Taake pura project ek hi tarah ke usoolon pe chale, koi shortcut na le.
- **Problem solve:** Bina rules ke, alag-alag hisson mein alag standards ban jate — ye ek jagah sab tay kar deta hai.

**`spec.md`**
- **Kya hai:** Desk kya-kya karega, iska poora behavior (kya hoga, kaise hoga) — bina code likhe.
- **Kyun hai:** Taake pehle decide ho jaye "kya banana hai", phir "kaise banana hai" sochein.
- **Problem solve:** Bina spec ke, coding agent apni marzi se decide kar leta ke edge cases mein kya karna hai — ye sab pehle likh diya.

**`plan.md`**
- **Kya hai:** Architecture — konse agents (Desk, Assignments, Careers) hain, konse tools hain, kaise data ka shape hai.
- **Kyun hai:** Taake pata ho system kaise banega, kaunsi cheez kis se connect hai.
- **Problem solve:** Ek naksha hai — bina isके, agent random decisions leta jaise "kaunsa agent kya karega".

**`tasks.md`**
- **Kya hai:** Chote-chote steps ki list, kis order mein karna hai.
- **Kyun hai:** Taake bade kaam ko chote pieces mein tod ke, ek-ek karke verify kiya ja sake.
- **Problem solve:** Bina isके, pata nahi chalta kya already ho chuka hai, kya baaki hai.

---

### ⚙️ Setup / Config Files

**`config.py`**
- **Kya hai:** Ek jagah jahan Gemini API key, model ka naam (`gemini-3.6-flash`), aur turn-limit (10) set hai.
- **Kyun hai:** Taake sab agents same settings use karein, alag-alag jagah copy-paste na ho.
- **Problem solve:** Agar model badalna ho (jaisa humein karna pada — 2.5 se 3.6), sirf ek jagah change karni padi.

**`courses.json`**
- **Kya hai:** Course, schedule, policy, aur assignment ka real data.
- **Kyun hai:** Taake AI khud se koi date ya policy invent na kare — sirf yahan se padhe.
- **Problem solve:** AI models kabhi galat cheez "confidently" bata dete hain — ye file real facts deti hai, guessing rok deti hai.

**`.env` / `.env.example`**
- **Kya hai:** `.env` mein asal secret keys (Gemini key, tracing key). `.env.example` mein sirf placeholder (dummy) values.
- **Kyun hai:** Secrets kabhi bhi GitHub pe public nahi jani chahiye.
- **Problem solve:** `.env` ko `.gitignore` mein daal diya — matlab kabhi commit nahi hogi, safe rahegi.

---

### 🧠 "Dimaagh" — Agents (Decision Makers)

**`desk_agent.py`**
- **Kya hai:** Main "receptionist" agent — Ops Desk. Har sawal pehle yahan aata hai.
- **Kyun hai:** Ye decide karta hai sawal kis type ka hai (assignment/career/admin) aur kahan bhejna hai.
- **Problem solve:** Ek hi jagah hai jo triage (decide) karti hai, baaki system organized rehta hai.

**`specialists.py`**
- **Kya hai:** Do specialist agents — Assignments (factual, seedha jawab) aur Careers (friendly, advice deta hai) — dono ek hi "Base" se clone hue hain.
- **Kyun hai:** Har topic ka apna expert hona chahiye, alag tone ke sath.
- **Problem solve:** Ek hi agent sab kuch karta to jawab ka tone confuse ho jata — ab har topic ka apna specialist hai.

**`student_profile.py`**
- **Kya hai:** Student ki information ka structure — naam, roll number, course, tier.
- **Kyun hai:** Ye information AI ko "context" ke zariye milti hai, seedha prompt text mein nahi.
- **Problem solve:** Agar naam seedha prompt mein likha jata, to ye "hardcoded" ho jata. Is tareeqe se har student ke liye dynamically (turant) profile banta hai.

**`ticket.py`**
- **Kya hai:** "Ticket" ka structure — category, summary, next_step, resolved (haan/na), escalate (haan/na).
- **Kyun hai:** Taake har jawab ek fixed, organized shape mein aaye — random text nahi.
- **Problem solve:** Plain text se computer ko samajhna mushkil hota — structured Ticket se system easily process kar sakta hai (jaise: "agar resolved=false hai to staff ko batao").

---

### 🖐️ "Haath" — Tools (Jo Agent Use Kar Sakta Hai)

**`tools.py`**
- **Kya hai:** Functions jo agent call kar sakta hai — course dekhna, assignment dekhna, account status check karna.
- **Kyun hai:** AI khud se data nahi janta — usay real data lene ke liye ye "tools" chahiye.
- **Problem solve:** Bina tools ke, AI guess karta. Tools se AI hamesha `courses.json` se real answer leta hai.

---

### 🛡️ Safety Aur Record-Keeping

**`guardrail.py`**
- **Kya hai:** Ek chhota check jo dekhta hai sawal bootcamp se related hai ya nahi.
- **Kyun hai:** Taake off-topic sawal (jaise "capital of France kya hai") ka jawab na diya jaye.
- **Problem solve:** Bina isके, Desk kisi bhi random sawal ka jawab deta rehta, jo galat hai for a "help desk" system.

**`audit.py`**
- **Kya hai:** Har conversation ka record rakhta hai — kaunsa agent, kab, kya kiya — ek file (`audit_log.jsonl`) mein.
- **Kyun hai:** Taake baad mein check kiya ja sake ke system ne kya kiya.
- **Problem solve:** Bina record ke, koi bhi masla hone pe pata nahi chalta kya hua tha — ye ek "flight recorder" jaisa hai.

**`run_support.py`**
- **Kya hai:** Ek chhota safety wrapper jo network glitch se recover karne ki koshish karta hai.
- **Kyun hai:** Abhi ye "inactive" (band) rakha hai — 1 hi try karta hai, retry nahi.
- **Problem solve:** Isay is liye band rakha kyunki Gemini ka apna retry system already kaam kar raha tha, isay dobara add karna sirf demo ke waqt risk badhata.

---

### 💻 Interface (Jahan Se User Baat Karta Hai)

**`main.py`**
- **Kya hai:** Terminal se test karne ka rasta — bina browser ke, seedha type karke.
- **Kyun hai:** Fast testing ke liye, development ke dauran.
- **Problem solve:** Har baar browser kholna slow hota — terminal se turant test ho jata hai.

**`app.py`**
- **Kya hai:** Browser interface (Chainlit) — asal demo yahan hoti hai.
- **Kyun hai:** User-friendly UI chahiye tha, sirf terminal kaafi nahi tha final product ke liye.
- **Problem solve:** Har student/user ke liye apna alag session hota hai — do log ek dusre ka data nahi dekh sakte.

**`.chainlit/config.toml`, `public/theme.json`, `chainlit.md`**
- **Kya hai:** Sirf UI ki looks — naam, color, welcome message.
- **Kyun hai:** Demo ko professional dikhane ke liye.
- **Problem solve:** Koi functional problem nahi — sirf presentation behtar banata hai.

---

### 🧪 Testing

**`scripts/live_verify_fr5_fr6.py`**
- **Kya hai:** Ek script jo automatically 6 alag sawal poochti hai aur check karti hai sahi agent ne jawab diya ya nahi.
- **Kyun hai:** Manually har baar test karna slow hai — ye ek hi baar mein sab check kar leta hai.
- **Problem solve:** Bina isके, har chhoti tabdeeli ke baad manually 6 sawal poochne padte.

---

## 3. 8 Viva Defense Questions — Chhote Jawab

**Q1. Profile-reading tool ka schema dikhao. Wrapper parameter kyun nahi hai?**
> Jawab: `get_account_status` tool sirf "context" se data padhta hai, model se nahi maangta. Isliye uske schema mein koi parameter hi nahi hai (empty). Ye FR-3 ka requirement tha — student ka naam kabhi prompt text mein hardcode na ho.

**Q2. Ek blocked (off-topic) sawal ka koi paisa (cost) nahi laga — trace se prove karo.**
> Jawab: Trace mein "Topic Guardrail" span dikhta hai jo Desk ke asal model call se PEHLE chalta hai. Agar guardrail reject kar de, Desk ka model kabhi call hi nahi hota — matlab koi extra paisa nahi lagta.

**Q3. Dono specialists (Assignments, Careers) Base se kya share karte hain, aur kya alag hai?**
> Jawab: Dono ek hi model (`gemini-3.6-flash`) share karte hain, Base se. Alag sirf instructions (Assignments = factual/cold, Careers = warm/friendly) aur temperature (0.1 vs 0.7) hai.

**Q4. Agar ek specialist ka naam badal do, kya toot jayega?**
> Jawab: Handoff registration us naam se hoti hai — agar naam badla to Desk uska reference nahi dhoond payega, handoff fail ho jayega. Naam `plan.md` aur `specialists.py` dono mein consistent hona chahiye.

**Q5. Chainlit handler `await` kyun karta hai? Agar na kare to kya error aayega?**
> Jawab: `await` isliye zaroori hai kyunki `Runner.run()` async hai — matlab result ka wait karna padta hai. Agar `await` na karein, to program result milne se pehle hi aage badh jayega, aur student ko blank ya adhoora jawab milega.

**Q6. Agar Ticket mein koi field missing ho, kaunsi exception aati hai, kis layer se?**
> Jawab: Pydantic validation error aata hai — jaise `summary` khali ho ya `category` galat value ho, to Ticket object banane ki koshish fail ho jati hai us layer pe jahan Pydantic model validate karta hai (`ticket.py`).

**Q7. Kaunsa hook har agent ke liye ek baar chalta hai, aur kaunsa har model call pe?**
> Jawab: `agent_start`/`agent_end` har agent ke liye ek baar (jab wo conversation "lete" hain aur "chhodte" hain). `tool_start`/`tool_end` har tool call pe alag se chalte hain — ek agent multiple tools call kar sakta hai.

**Q8. Custom runner (FR-11) kyun nahi bana?**
> Jawab: Time kam tha, isliye `spec.md` ke apne "cut list" (§7) ko follow kiya — jismein FR-11 sabse pehle drop karne wali cheez thi (priority 1). Ye deliberate decision hai, likha hua hai spec mein — accident nahi.

---

## 4. Quick FR Reference Table (agar koi bhi FR number pooche)

| FR | Kya karta hai | Status |
|---|---|---|
| FR-1 | Gemini se connect, terminal se chalna | ✅ Done |
| FR-2 | Course data sirf tools se milna | ✅ Done |
| FR-3 | Student ka naam context se, prompt se nahi | ✅ Done |
| FR-4 | Har turn pe alag instructions (naam, tone) | ✅ Done |
| FR-5 | Do specialists, handoff se | ✅ Done |
| FR-6 | Summariser ek tool ke taur pe | ✅ Done |
| FR-7 | Har jawab ek structured Ticket | ✅ Done |
| FR-8 | Off-topic sawal reject karna | ✅ Done |
| FR-9 | Scholarship-only tool, close_ticket, turn-limit | ✅ Done |
| FR-10 | Har conversation ka record (audit log) | ✅ Done |
| FR-11 | Custom runner (request id + time) | 🔪 Cut kiya, wajah likhi hui hai |
| FR-12 | Browser interface (Chainlit) | ✅ Done |
| FR-13 | Tracing (OpenAI dashboard pe trace) | ✅ Done |

**Agar sir poochein "sab kuch complete hai?"** → *"13 mein se 11 poori tarah ban chuki hain aur live test ho chuki hain, 1 (FR-11) deliberately time ki wajah se cut ki hai jo spec mein already likha tha ke agar time kam pare to sabse pehle yehi drop karna."*

---

## 5. Ek Aakhri Baat

Kal agar koi aisi cheez pooche jo yaad na aaye, ye bolo:
> *"Ye decision maine `plan.md`/`spec.md` mein likha hua tha, wahan dekh kar bata sakta hoon."*

Ye bilkul sahi jawab hai — poora point hi ye tha ke specs likh kar rakhi jayein taake har decision traceable ho.

**All the best! 🎯**
