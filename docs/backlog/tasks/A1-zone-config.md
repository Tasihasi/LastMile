# A1 — Zone config (irányítószám → zones)

**Email §1** · **P0** · **Depends on:** — · **Size:** S · **Status:** implemented on `feature/a1-zone-config` (data from Gergő's 2026-11-17 daily sheet)

## Goal
A single, data-driven source of truth mapping each zip to a sorting zone. Data comes from Gergő's 2026-11-17 sheet: 34 zips (districts V–IX) in 16 zones.
Zones are geographic units that should normally travel together (e.g. 1082 + 1083 = Baross / Üllői / József krt. / Illés u. rectangle).

## Context
- Depot: Orczy út 45 (VIII. ker.).
- Existing: `backend/planner/districts.py` only knows districts, not zones.

## Scope
- New module `backend/planner/zones.py` + data file `backend/planner/zones.json` (`{"zones": [{"id": "Z01", "name": "...", "zips": ["1082","1083"]}, ...]}`).
- API: `zone_for_zip(zip) -> zone_id | None`, `zips_in_zone(zone_id)`, `all_zones()`, `validate_config()`.
- Endpoint `GET /api/zones/` (planner-only) returning the config (used later by UI).
- A stand-in file may carry `"_placeholder": true`; startup then logs a warning. The bundled `zones.json` is real data, so no warning.

## Acceptance criteria
- **A1-AC1** Every zip appears in exactly one zone (validator raises on duplicates).
- **A1-AC2** Config contains exactly 16 zones and 34 zips *when `_placeholder` is false*.
- **A1-AC3** `zone_for_zip("1083") == zone_for_zip("1082")` ; unknown zip → `None`.
- **A1-AC4** `GET /api/zones/` → 200 for planner, 403 for biker, 401 anonymous.
- **A1-AC5** Malformed JSON / zip not matching `^1\d{3}$` fails `validate_config()` with a message naming the offending entry.

## Test plan
- U: `test_zones.py` — AC1, AC2, AC3, AC5 (feed broken configs via a `load(path)` parameter).
- A: `test_e2e_api.py` — AC4 using planner + biker clients.

## Data notes (from the sheet)
- The 16 zone groups (bottom-left block) cover exactly the 34 zips of districts V–IX.
- Zips outside that set (1111, 1113, 1114, 1115, 1117, 1123: XI./XII.) appear in the daily sheet but have no zone; `zone_for_zip` returns `None` for them. How to allocate them is for A2/A5.
- Daily assignments sometimes split a group across bikers (e.g. 1054 / 1055), so zones are a default grouping, not a hard rule.

## Out of scope
Using zones in allocation (A2/A5), editing zones in a UI.

---

## Original source (Gergő's email, 2026-11-17, Hungarian, verbatim)

ecsatolom Barnát, hogy ő is lássa a folyamatot, illetve munkamegosztásról is volt szó.

Ma végignéztük azt, amit az előző hosszabb levelemben írtam a szoftver végigpróbálása után, és ez alapján megbeszéltük, hogy mik a következő lépések, és ebben a mi a prioritás. Vannak olyan elemek, amik nélkül nem tudjuk elkezdeni használni (ez az elsődleges) és vannak olyanok, amelyek segítenék tovább egyszerűsíteni/gyorsítani a folyamatot, vagy még pontosabb tervezést tennének lehetővé.

1. A legrészletesebben az optimális elosztásról beszéltünk, az irányítószámok figyelembe vételével.
Itt a minimum kritérium az, hogy 1 irányítószámhoz tartozó csomagokat csak 1 körhöz osszon, ne fordulhasson elő olyan, hogy ugyanazon irányítószámú csomagok több különböző kör között vannak elosztva. (Különben a szortírozás is túl hosszúra nyúlik, illetve nem tudjuk lekövetni, hogy az egyes csomagok 48 órás kézbesítési határidejét tudjuk-e tartani mert nem tudjuk hogy melyik csomagokat próbáltuk meg az adott napon és melyikeket nem - ezt csak az irányítószámokat figyelve tudjuk számontartani.) Ha ez a feltétel teljesül, akkor már tudjuk használni a szoftvert, még akkor is, ha a szoftver magától rosszul kombinálná az irányítószámokat - ha megvan az a lehetőség, hogy te felülírd és átpakolj egy irányítószámot egy másik futárra. Hiszen most is a diszpécser agya végzi el ezt a kombinációt, csak a LastMile-ban kap hozzá egy vizuális segédeszközt (előre-vissza lépés a térkép nézetből), valamint utána külön-külön optimalizálja az útvonalakon belül a sorrendet, és minden előny érvényesül, ami ezzel jár, ami nagy előrelépés a mostani állapothoz képest.
De ennél bővebben beszéltünk erről:
Elmondtam, hogy van jelenleg az elsődleges területünkön 34 irányítószám (az 5-6-7-8-9 kerületekben, a konkrét lista itt van), és ebből mi a szortírozáshoz 16 csoportosítást képzünk, ami szintén látható a linkelt táblázatban 22. sortól. A 16 csoportosítás (zóna) egyúttal földrajzi szempontból is logikus egység (amennyire ez lehetséges), tehát pl. a 1082 és 1083 irányítószámra eső csomagokat, ami egy zóna szinte mindig érdemes együtt vinni, mert ez a Baross, Üllői, József körút és Illés utca közötti téglalap, és egymás mellett lévő címek vagy 1082 vagy 1083 irányítóval szerepelnek. Ezért lehetne olyan logikai sorrendben elvégeztetni a kiosztás műveletét, hogy először próbálja meg a 16 zónához tartozó csomagokat optimálisan elosztani a körök között, hogy a leginkább feltöltse a rendelkezésre álló időt. Aztán ha ez nem sikerült, mert maradt olyan zóna, amit nem tudott kiosztani, mert egyik kör idejébe se fér bele, pedig összesen rendelkezésre állna a szükséges idő (mert mindenki hamarabb végez), akkor bontsa szét a zónákat (lehetőleg minél kevesebb zónát, vagyis csak annyit bontson meg, amennyit muszáj ahhoz, hogy ki tudjon osztani minden csomagot), és egy-egy irányítószámhoz tartozó csomagot tegyen át egy másik körhöz. Egyúttal végig fontos a földrajzi szempont, vagyis hogy egy körhöz olyan zónákat/irányítókat csoportosítson egybe, amelyek az Orczy út 45-ből kiindulva és ide visszatérve a legrövidebb útidővel teljesíthetőek. Én egyébként elég bizonytalan vagyok, hogy mennyire lehetséges leprogramozni ezt a modellt, szóval ha kiderül, hogy ez nem működőképes, akkor gyorsan egyeztessünk, hogy kitaláljunk valami más logikát, és közben is gondolkozom ezen.

2. A körökre osztás lépésénél ("Bikers") meg lehessen adni a depóból elindulás és a depóba visszatérés időpontját ami kiadja a maximálisan rendelkezésre álló időt. A depóból elindulás a közös határideje a diszpécsernek, a futárnak és mindenkinek aki a depóban dolgozik azon, hogy az adott kör be legyen pakolva és készen álljon minden addig a pillanatig ahhoz, hogy a futár le tudja nyomni a pedált és meginduljon. A depóba visszatérés a futár határideje hogy teljesítse azt a kört, amit a megadott paraméterek alapján tudnia kellene teljesítenie. A tervező felelőssége, hogy olyan paramétereket adjon meg, amelyek valóban teljesíthetőek (egy címen töltött idő + átlagos útidő + szünet). Ezt az elején biztos sokat kell variálnunk ahhoz, hogy kijöjjönek a reális számok. De adjuk meg azt a lehetőséget, hogy az egy útra szánt időt max 7.5%-al túllépje (és ekkor a diszpécser egyeztet a futárral arról, hogy oké-e neki vagy sem a túlóra). Elsőre elég, ha az útidőt, egy címen töltött időt teljesen általánosan lehet megadni (csak egy helyen kell átírni), és ennek nem is feltétlen kell még felhasználói felület, csak a kódban írod át. Itt másodlagos szempont (későbbi fejlesztés), hogy lehessen a futárok adatlapjához rendelni egyedi szorzót, ami a megadott alap címen töltött időt csökkenti vagy növeli. Pl. ha az egy címen töltött idő alapból 2 perc címenként, akkor egy átlagos futár szorzója 1 (2 perc), egy betanulósé 2 (4 perc), egy gyors futáré 0.85 (1.7 perc), és lehessen az útvonalaknál külön szerkeszteni a címen töltött időt (például az 5. kerületben szinte csak munkahelyi címek vannak, ahol sokszor a bejáratnál átveszik a csomagot, a 6-7. kerületben meg sok társasházban nincs lift, és sokat kell lépcsőzni, érezhetően lassabban lehet haladni).

3. A feltöltésnél hozzon létre egy új adatoszlopot, amibe minden sorhoz a feltöltött file nevét másolja be. Mi pedig az importálás előtt átnevezzük azt a 2 max 3 filet amit feltöltünk annak a cégnek a nevére, ahonnan kiszedtük a csomaglistát. (pl: "csomagkézbesítés lista 2611131236" -> "fáma", parcels 11132026 -> "imile"). Ez két helyen kell: a későbbi excel exportnál amit a csomagok fizikai sorba rendezéséhez használunk, és a térképes megjelenítésnél, hogy a futár tudja, hogy melyik alkalmazásban keresse ki a csomagot (mert onnan kell hívja az ügyfelet, és ott kell beolvasnia a vonalkódját hogy tudja adminisztrálni), melyik zsákjából keresse ki a csomagot. A legjobb, ha a különböző cégek különböző színnel jelennek meg az útvonalban, de az is lehet, hogy a listanézetben ezt az adatot is feltünteti (anélkül, hogy külön rá kelljen nyomni valamire). Másodlagos fejlesztés (ráér), hogy a táblázatok fejlécét meg tudja feleltetni az elvárt karakterláncnak. A táblázatok mindig ugyanazon formátum szerint érkeznek, szóval például a Fáma exportban mindig ott lesz a cím, hogy "Cím", vagy iMile exportban ott, hogy "Address" tehát ha megadod neki, hogy "Cím" = "Address" = address, akkor az mindig működni fog. Most jöttem rá, hogy a végén az excel exporthoz kelleni fog minden releváns oszlop megfeleltetése. Erről írok az 5. pontban.

4. Futár felhasználóból telefonon látható legyen nagyjából párhuzamosan a lista nézet és a térkép nézet. (Például úgy, hogy elhúzod oldalra, majd 'összecsukod'). Ez gyorsítja nagyban a reggeli bepakolást, egy tapasztalt futárnál gyorsítja a következő címre elindulást (ha fejből tudja, hova megy csak a cím alapján, akkor a térképre rá se kell néznie), és segíti, hogy az egy címre menő csomagokat kiszúrja (mert egymás alatt lesznek a listában).

5. Excel export a folyamat végén, amiben szerepel minden adott naphoz tartozó csomag, ezen adatoszlopokkal:
a) csomagazonosító
b) cím (irányítószám, utca, házszám)
c) cég (fáma/imile stb.)
d) futár neve
e) sorrend száma (az adott útvonalból hanyadik) - itt rájöttem, hogy a bepakolásnál azt is látnunk kell, hogy mennyi van összesen, különben nem tudjuk, hogy mikor vagyunk készen, tehát vagy az export legyen olyan, hogy 1/45, 16/45, vagy esetleg lehet úgy, hogy két oszlop legyen, sorrend száma (1, 16) és egy másik oszlopba minden sornál hogy hány csomag van összesen azon a körön, és akkor a megjelenítésnél lehet játszani azzal hogy melyik szám mekkora, hogy minél olvashatóbb legyen (pl. 16/45), erre Barna lehet h van jó ötleted

6. 97%-os pontosságú geocoding szolgáltató kiválasztása - erről azt beszéltük, hogy Barnának lehetne a feladata, ha te is vállalod, és a RouteXL-re fizetnénk elő egy olyan napra, amikor tudsz vele egyben többet foglalkozni, mert ott kapásból 5 szolgáltatót lehet tesztelni, és így 2000 Ft-ért (egy napi díj, bármennyi 100 címes útvonalat enged), és össze lehet hasonlítani hogy ugyanazon mintából melyik szolgáltató milyen pontossággal dolgozik. A pontos kutatási módszertant kitalálni kicsit bonyeszebb azért, mert azt sokkal nehezebb kiszűrni (én most csak szemre tudnám), hogy pontosan helyezte-e el a térképen, vagy sem, és mi ebben az arány a különböző szolgáltatók között. De lehet, hogy itt a LastMile-hoz is kell majd hozzáférés, és jó lenne, ha ti ketten tudnátok egyeztetni.
A LastMile-ban kell az a lehetőség, hogy bármely ponton még javítani lehessen a címeket. tehát ha valamit rosszul helyezett el, akkor vissza lehessen menni a legelső lépéshez, és tovább szerkeszteni a szöveges címet és/vagy áthelyezni a térképen drag and drop módon a pöttyöt. Enélkül azért nem tudjuk használni a szoftvert, mert ha Pilisvörösvárra dobja a Golgota utca 4-et (mint a példában amit néztünk), akkor se a körökre osztás, se annak az útvonalnak az optimalizálása nem működik már, tehát egy rossz cím haza tudja vágni az egészet. Mondjuk most még az jutott eszembe, hogy ha tényleg csak 1-2 cím van nagyon rossz helyen, akkor tudjuk törölni az útvonalból, csak akkor meg a futárnak kell észben tartania, hogy igazából még az is van neki. Szóval végülis ettől még jelenleg is használható a szoftver, ez nem kizáró ok.

7. Pár bugos dolog javítása, amit a korábbi levelemben kifejtettem: visszalépési lehetőség egy útvonalból a több útvonal egyszerre nézésébe, a futár nézetből ne lehessen tovább osztani a kört, stb.

+ (szintén későbbi) A behívott szolgáltatások API-jait egy helyen tudja egy admin felhasználó változtatni, tehát a tárhely, geocoding, route optimization, adatbázis - mellette egy-egy mező ahová az API-kulcsot be lehet másolni. Így az időszakosan frissítendő API-kat meg lehet újítani, vagy fejlesztő közbenjárása nélkül lehet szolgáltatót cserélni. Az összes külsö szolgáltatásra együtt havi 20-80 ezer forintunk van, ha ebből nem jönne ki, akkor gondolkozzunk tovább.

+Sorrend szerinti szortírozást segítő app. Azt beszéltük meg Danival is Barna, hogy ez egy külön app legyen a LastMile-tól. Ha benne vagy, te tudnál ezen párhuzamosan dolgozni, és arról kell folyamatosan egyeztetni, hogy milyen excelt adjon ki a LastMile, amit a szortapp be tud venni. Erre már most csinálhatnánk egy dummy excelt, amivel aztán lehet tesztelni.

Linkelem még azt a táblázatot, amiben összeszedtem hogy mit kell tudnia (bármilyen) tervezőszoftvernek amit használunk.

Az beszéltük meg, hogy jövő hét végéig Dani az 1-es ponttal fogsz dolgozni, és akkor egyeztetünk róla megint.

üdv,

