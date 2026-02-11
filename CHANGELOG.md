# Ændringer

Oversigt over nye funktioner og ændringer i Basal-systemet, siden 16. januar 2026

---

## 11. februar 2026

### Filtrér og sortér skoler efter skoleår
Skolelisten har nu en skoleår-dropdown, der filtrerer skoler efter det skoleår de blev tilmeldt i. Kolonnen "Tilmeldt skoleår" er nu også sorterbar. Dropdown viser kun skoleår hvor der faktisk er tilmeldte skoler.

### Filtre aktiveres automatisk
Alle dropdown-filtre på skolelisten aktiverer nu søgningen med det samme — man behøver ikke klikke på Søg-knappen.

### Eksport matcher nu tabelkolonner
Excel-eksporten fra skolelisten og kursuslisten er opdateret, så kolonnerne matcher de kolonner man ser i tabellen (Status, Skoleår, Pladser for skoler; Dato, Sted, Undervisere, Tilmeldinger, Status for kurser).

---

## 9. februar 2026

### "Aktiv fra" vises nu som skoleår-chip
I stedet for en rå dato vises "Aktiv fra" nu som en farvet badge med skoleåret (fx "2024/25"). Hvert skoleår har sin egen farve, så de er nemme at skelne fra hinanden. Ændringen gælder på skolelisten, skoledetaljesiden og tilmeldingsbekræftelsen.

### Skoleår-dropdown ved redigering af tilmeldingsdatoer
Når man redigerer en skoles tilmeldingsdatoer, vælger man nu skoleår fra en dropdown i stedet for at vælge en dato. Dropdown viser 5 skoleår startende fra tilmeldingsåret.

### Nulstil tilmelding
På siden "Rediger tilmeldingsdatoer" er der nu en knap til at nulstille alle tilmeldingsdatoer (tilmeldt, aktiv fra og frameldt), hvis en skole blev tilmeldt ved en fejl.

### Koordinator-info på kursustilmeldingssiden
Når en skole vælges på kursustilmeldingssiden, vises nu koordinatorens navn og kontaktoplysninger. Der er også et link til skolens side, hvor kontaktoplysningerne kan redigeres.

### Forbedret filvisning
Fillisten på skoledetaljesiden viser nu beskrivelsen øverst, derefter dato og uploader, og filnavnet i monospace nederst. Lange filnavne afkortes med ellipsis.

---

## 5. februar 2026

### Ny pladsberegning: Første år og Forankring
Pladsberegningen er redesignet fra en samlet tæller til to separate grupper:

- **Første år (3 pladser):** Skoler får 3 gratis pladser i deres første skoleår. Ubrugte pladser overføres ikke til næste år
- **Forankring (1 plads):** Efter første år får skolen 1 gratis plads til at forankre projektet. Denne plads gælder for hele perioden efter første år
- **Ekstra pladser:** Skoler kan altid tilmelde flere end de gratis pladser — de vil blive faktureret for ekstra pladser

### Dynamiske infobokse på kursustilmeldingssiden
Når en skole vælger kursus på tilmeldingssiden, vises nu en infoboks der tilpasser sig automatisk:

- Viser om skolen har ledige pladser eller skal betale for ekstra pladser
- Inkluderer priser for ekstra pladser og info om hvad en plads inkluderer
- Teksten kan redigeres i admin under "Pladsinformation"
- Opdateres dynamisk når deltagere tilføjes eller fjernes

### Forbedret pladsvisning på skolesider
Både medarbejder- og offentlige skolesider viser nu pladser i to grupper:

- **Første år:** Viser skoleår, antal pladser, brugte og ledige
- **Forankring:** Viser antal pladser brugt efter første år
- Den aktuelle periode fremhæves, den anden vises nedtonet
- Medarbejdersiden viser advarsel hvis skolen bruger ekstra pladser ud over de gratis

### Fjernet ekstra-pladser-køb
`SeatPurchase`-modellen er fjernet. Ekstra pladser håndteres nu implicit via fakturering.

### Pladsvisning på skolelisten viser nu kun aktuel periode
Kolonnen "Ubrugte pladser" er omdøbt til "Brugte pladser" og viser nu kun den aktuelle periodes pladser (første år eller forankring) i stedet for summen af begge perioder. Kolonnens label (fx "Første år" eller "Forankring") vises under tallet.

### Ny status: "Tilmeldt fra næste år"
Skoler der er tilmeldt men først aktive fra næste skoleår vises nu med en særskilt status:

- **Statusbadge:** "Tilmeldt fra næste år" (blå) i skolelisten
- **Filtrering:** Ny filtermulighed i skolelisten
- **Pladswidget:** Viser ventebesked med info om hvornår pladserne bliver tilgængelige
- **Aktiv fra-dato:** Sættes nu korrekt til tilmeldingsdatoen når den ligger i fremtiden

### Nøgletal på skolelisten
Tre kort vises øverst på skolelisten:

- **Skoler med nuværende filtre** — antal skoler der matcher aktive filtre
- **Skoler tilmeldt nu** — antal aktuelt tilmeldte skoler
- **Skoler nogensinde tilmeldt** — antal skoler der har været tilmeldt på et tidspunkt

### Dashboard: Tilmeldingsdato i stedet for ubrugte pladser
"Seneste tilmeldinger til Basal" på forsiden viser nu tilmeldingsdato i stedet for ubrugte pladser.

### Skolelisten: Tilmeldt skoleår
Kolonnen "Seneste henvendelse" er erstattet med "Tilmeldt skoleår" der viser i hvilket skoleår skolen blev tilmeldt Basal.

### Kursuspåmindelser sendes nu 14 dage før
Den automatiske påmindelsesmail til kursusdeltagere sendes nu 14 dage før kursusstart i stedet for 2 dage.

### Redigering af filer og kursusmaterialer
Det er nu muligt at redigere eksisterende skolefiler og kursusmaterialer:

- **Skolefiler:** Rediger beskrivelse eller erstat filen fra skoledetaljesiden
- **Kursusmaterialer:** Rediger navn eller erstat filen fra kursusdetaljesiden
- Filen kan erstattes uden at ændre andre felter, eller man kan opdatere kun navn/beskrivelse

### Forbedret infoboks på kursustilmeldingssiden
- Viser nu pladsstatus efter tilmeldingen (fx "2 brugt ud af 3 — 1 ledig")
- Kun én infoboks i stedet for to separate bokse
- Infoboksen er flyttet til lige over tilmeld-knappen
- Fjernet udråbstegn og "Godt gået!" fra teksterne

---

## 4. februar 2026

### Forbedret håndtering af tilmeldingsdatoer
Ny funktion til at styre hvornår en skoles tilmelding træder i kraft:

- **Aktiv fra-dato:** Ny dato der bestemmer hvornår tilmeldingen får effekt på pladser og forankring
- **Automatisk beregning:** Hvis en skole tilmelder sig efter sidste kursustilmeldingsfrist, sættes "aktiv fra" automatisk til næste skoleårs start
- **Redigering:** Medarbejdere kan redigere både tilmeldingsdato og aktiv fra-dato via "Rediger tilmeldingsdatoer" på skoledetaljesiden
- **Offentlig tilmelding:** Ved tilmelding efter fristen informeres skolen om at deres tilmelding træder i kraft fra næste skoleår

### Forbedret bekræftelsesmail ved skoletilmelding
Bekræftelsesmailen til skoler ved tilmelding bruger nu en redigerbar e-mail skabelon:

- **Skabelonstyring:** Teksten kan nu redigeres i admin under E-mail skabeloner
- **BCC-kopi:** Alle bekræftelsesmails sendes nu med BCC til basal@sundkom.dk (kan ændres via miljøvariabel)
- **Tilgængelige variabler:** `{{ contact_name }}`, `{{ school_name }}`, `{{ school_page_url }}`, `{{ signup_url }}`, `{{ signup_password }}`, `{{ site_url }}`

### Fjernet notifikationsabonnement
Den tidligere funktion hvor brugere kunne abonnere på notifikationer ved nye skoletilmeldinger er fjernet. I stedet modtages alle bekræftelsesmails nu automatisk på basal@sundkom.dk.

---

## 3. februar 2026

### Opdelt personvisning på skolens offentlige side
Skolens offentlige side viser nu personer i to separate bokse:

- **Kontaktpersoner:** Skolens primære kontakter med roller og kontaktoplysninger
- **Kursusdeltagere:** Personer der har deltaget i kurser men ikke er registreret som kontaktpersoner

### Redigering fra skolens offentlige side
Skoler kan nu selv administrere deres personer direkte fra den offentlige side:

- **Kontaktpersoner:** Tilføj nye, rediger eksisterende, eller slet personer der ikke længere er tilknyttet
- **Kursusdeltagere:** Rediger titel og email på personer der har deltaget i kurser

Dette gør det muligt for skoler at holde deres oplysninger opdateret uden at kontakte Basal.

### Badges for kursusdeltagelse
Kursusdeltagelse vises nu med farvede badges i stedet for tekst:

- **Uddannet** (grøn) - deltog i kurset
- **Mødte ikke op** (rød) - udeblev fra kurset
- **Tilmeldt** (grå) - tilmeldt fremtidigt kursus

### Nye rollefelter på kontaktpersoner
Kontaktpersoner har fået to nye afkrydsningsfelter:

- **Koordinator:** Markerer skolens primære kontaktperson for Basal
- **Økonomisk ansvarlig:** Markerer personen der håndterer fakturering

En person kan nu have begge roller, én rolle, eller ingen. Rollerne vises som farvede badges på skoledetaljesiden og skolens offentlige side:
- Koordinator vises med blåt badge
- Økonomisk ansvarlig vises med gråt badge

Dette erstatter det tidligere "Primær kontakt"-felt og rolle-dropdown.

---

## 30. januar 2026

### Udvidede skoleoplysninger
Skoler har fået flere felter til bedre administration:

- **Postnummer og by:** Separat fra adressefeltet for mere struktureret data
- **EAN-nummer:** Til fakturering via offentlige indkøbssystemer
- **Titel på personer:** Kontaktpersoner kan nu have en titel (Skoleleder, Viceskoleleder, Lærer, SFO-leder, Pædagog, Andet). Ved "Andet" kan man indtaste en brugerdefineret titel

### Faktureringsoplysninger
Ny sektion på skoledetaljesiden til faktureringsoplysninger:

- **Kommunal betaling:** Markér om fakturaen skal sendes til kommunen i stedet for skolen
- **Faktureringskommune:** Vælg hvilken kommune der skal faktureres
- **Faktureringsadresse og EAN:** Kommunens faktureringsoplysninger

Disse felter udfyldes også automatisk ved skoletilmelding hvis skolen angiver at kommunen betaler.

### Advarsel om manglende oplysninger
Skoledetaljesiden viser nu en advarselsboks hvis vigtige oplysninger mangler (f.eks. EAN-nummer når kommunen betaler). Dette hjælper med at sikre at alle nødvendige data er på plads før fakturering.

### Forbedret fakturaformular
- **Automatisk skoleårsvalg:** Skoleåret forvælges baseret på den aktuelle dato
- **Begrænset årsvalg:** Kun indeværende og tidligere skoleår kan vælges (ikke fremtidige)

### Danske datoer på kurser
Kursustitler viser nu altid datoer med danske månedsnavne (jan, feb, mar, apr, maj, jun, jul, aug, sep, okt, nov, dec) uanset serverens systemsprog.

### Mindre forbedringer
- Søgeknappen på skolelisten viser nu en loading-animation mens der søges
- Login-sektionen på skoledetaljesiden hedder nu "Kodeord og links" for klarhed

### Filupload per skole (intern)
Medarbejdere kan nu uploade filer til hver skole direkte fra skoledetaljesiden. Filer er kun synlige for medarbejdere og vises ikke på skolens offentlige side. Hver fil kan have en beskrivelse, og alle filuploads logges i aktivitetsloggen.

### Kursusdeltagelse på skolens offentlige side
Skolens offentlige side viser nu kursusdeltagelse for kontaktpersoner. Under hver kontaktperson vises hvilke kurser de har deltaget i med status:
- "Uddannet på" - for deltagere der mødte op
- "Mødte ikke op til" - for deltagere der udeblev
- "Tilmeldt" - for fremtidige kurser

### Kursusdeltagere-sektion på offentlig side
En ny "Kursusdeltagere"-sektion viser personer der har deltaget i kurser men som ikke er registreret som kontaktpersoner for skolen. Dette giver et komplet overblik over alle fra skolen der har været på kursus.

### Kursusmaterialer på skolens offentlige side
Skoler kan nu downloade kursusmaterialer direkte fra deres offentlige side. Sektionen "Kursusmaterialer" viser materialer fra alle kurser skolen har deltaget i, sorteret med de nyeste kurser først.

---

## 27. januar 2026

### Faktura-skoleår ændret til enkeltvalg
Fakturaer har nu kun ét skoleår i stedet for flere. Dropdown-menuen til valg af skoleår er blevet mere kompakt og viser kun de skoleår skolen er tilmeldt i.

### Unik fakturanummer per skoleår
Systemet forhindrer nu at oprette to fakturaer med samme fakturanummer for samme skoleår. Ved forsøg på at oprette en dublet vises en tydelig fejlbesked.

### Fjernet skoleårsredigering
Menupunktet "Skoleår" er fjernet da skoleår nu oprettes automatisk og ikke behøver manuel redigering.

### Forbedret visning af manglende fakturaer
Listen over manglende fakturaer er blevet forbedret:

- **Kun relevante skoleår:** Viser kun indeværende og forrige skoleår
- **Kun relevante skoler:** Viser kun skoler i forankring eller skoler der har brugt flere pladser end de har fået tildelt
- **Fakturatype:** Viser tydeligt om der mangler en "Forankring"-faktura eller en faktura for ekstra pladser
- **Separate fakturaer:** Skoler der både er i forankring og har brugt ekstra pladser vises med to separate linjer
- **Alfabetisk sortering:** Listen er nu sorteret alfabetisk efter skolenavn

### Rettet kolonner i dashboard
Kolonnevisningen i "Kommende kurser" på dashboardet er rettet så kursus, dato, sted og tilmeldinger vises korrekt.

### Forbedret bulk import af kursustilmeldinger
Bulk import er blevet forbedret med ny kolonnerækkefølge og bedre håndtering af data:

- **Ny kolonnerækkefølge:** Fornavn, Efternavn, Tlf., Mail, Skole, Underviser
- **Håndtering af "Skole, Kommune"-format:** Systemet genkender nu skoler skrevet som "Ravnshøj Skole, Frederikshavn Kommune" og matcher automatisk til den rigtige skole
- **Anden organisation:** Deltagere der ikke er fra en skole (f.eks. fra kommunen) kan nu importeres ved at vælge "Anden organisation" og indtaste organisationens navn
- **Opret ny skole:** Hvis en skole ikke findes i systemet, kan den oprettes direkte under importen med navn og kommune
- **Redigerbare felter:** Telefon og underviser-status kan nu redigeres i bekræftelsestrinnet før import

### Filter for skoler med kurstilmeldinger uden Basal-tilmelding
Nyt filter på skolelisten: "Har kurstilmeldinger (ikke tilmeldt)" viser skoler der har deltagere tilmeldt kurser, men som ikke selv er tilmeldt Basal. Dette hjælper med at identificere skoler der bør kontaktes om tilmelding.

### Tilmeldingsfrist på kurser
Kurser har nu en tilmeldingsfrist som automatisk sættes til 5 uger før kursusstart. Efter fristen vises kurset ikke længere på den offentlige tilmeldingsside. Fristen kan tilpasses manuelt for hvert kursus.

### Forbedret kursusvisning på tilmeldingssiden
Når man vælger et kursus på tilmeldingssiden, vises nu et detaljekort med:
- Dato
- Sted (fuld adresse)
- Tilmeldingsfrist
- Undervisere
- Ledige pladser

Kursustitlen i dropdown viser nu også lokationens by/kommune, f.eks. "Kompetenceudviklingskursus, 15. mar 2026 - København".

### Flere kurser på samme dato
Det er nu muligt at oprette flere kurser med samme start- og slutdato. Begrænsningen er fjernet da det kan være relevant at afholde flere kurser samme dag forskellige steder.

### Om-side med ændringslog
Der er tilføjet en "Om Basal"-side på `/om/` som viser systemets ændringslog. Siden er tilgængelig fra brugermenuen og giver overblik over nye funktioner og ændringer.

### Tilmeldingshistorik på skolens side
Skoler kan nu se deres fulde tilmeldingshistorik når de besøger deres offentlige side på `/school/<token>/`. Historikken viser hvornår skolen blev tilmeldt og eventuelle frameldinger over tid.

### Nyt link til skolens offentlige side
I login-sektionen på skolesiden er der nu et direkte link til "Skolens side", så skoler nemt kan finde deres offentlige profil. "Direkte link" er desuden omdøbt til "Tilmeldingslink" for at gøre det tydeligere hvad linket bruges til.

### Forbedret kursussletning
Når man sletter et kursus, vises nu en oversigt over hvad der vil blive slettet (antal tilmeldinger og kursusmaterialer). Knappen hedder nu "Slet permanent" for at gøre det tydeligt at handlingen er permanent.

### Handlingsknapper på kursusredigering
Kursusredigeringssiden har nu de samme handlingsknapper som kursusdetaljesiden: "Vis", "Fremmøde" og "Slet permanent". Dette gør det nemmere at navigere uden at skulle tilbage til detaljesiden først.

### Forbedrede emails
- Link til skolens offentlige side er tilføjet i bekræftelsesmailen ved tilmelding
- Alle emails indeholder nu en kontaktfooter med basal@sundkom.dk, så modtagere nemt kan komme i kontakt

---

## 26. januar 2026

### Forbedret kursusadministration
Kurser har fået en helt ny struktur der gør det nemmere at administrere undervisere og lokationer:

- **Automatisk kursustitel:** Kursustitlen genereres nu automatisk som "Kompetenceudviklingskursus, 1. feb - 3. feb 2026" baseret på de valgte datoer
- **Undervisere:** Vælg op til 3 undervisere fra en dropdown-menu. Undervisere kan genbruges på tværs af kurser, og nye undervisere kan tilføjes direkte fra formularen med "+ Tilføj ny"
- **Lokationer:** Vælg lokation fra dropdown med navn, adresse, postnummer og by. Nye lokationer kan også tilføjes direkte fra formularen
- **Redigering af tilmeldinger:** Alle felter på en kursustilmelding kan nu redigeres (navn, email, telefon, titel, skole)
- **Bulk import:** Importformatet er opdateret til 6 kolonner (fornavn, efternavn, skole, email, telefon, er_underviser)

### Telefonnummer på kursustilmelding
Der er tilføjet et valgfrit telefonnummer-felt når man tilmelder deltagere til kurser. Telefonnummeret gemmes på tilmeldingen og kan bruges til at kontakte deltageren.

### Skoleadresse er nu valgfri
Adressefeltet på skoler er nu valgfrit, da kommune ofte er tilstrækkeligt til at identificere en skole.

### Ny kontoindstillingsside
Alle brugere kan nu selv redigere deres profil og skifte adgangskode uden at kontakte en administrator. Siden findes på `/account/settings/`.

### Skolens offentlige side
Skoler kan nu tilgå en offentlig visning af deres egen status via et unikt link. Siden viser:

- Skolens tilmeldingsstatus (tilmeldt/frameldt)
- Antal pladser og hvor mange der er brugt
- Liste over alle tilknyttede personer
- Historik over tilmeldinger og frameldinger

Linket sendes til skolen ved tilmelding og kan også findes i login-sektionen.

### Samlet personoversigt
Personer og kursustilmeldinger er nu samlet i én oversigt på skoledetaljesiden. Listen viser alle personer med direkte links til deres kurser og fremmødebadges, så man hurtigt kan se hvem der har deltaget i hvilke kurser.

### Kommune vælges fra liste
Kommune vælges nu via en dropdown-menu med alle 98 danske kommuner i stedet for et fritekstfelt. Dette sikrer ensartet stavning og gør det nemmere at filtrere skoler efter kommune.

### Tilmeld/Frameld-knap
Ny knap på skoledetaljesiden til at tilmelde eller framelde skoler fra Basal. En modal åbnes hvor man kan vælge den præcise dato for tilmelding eller framelding.

### Beskyttelse mod dubletskoler
Systemet forhindrer nu oprettelse af dubletskoler: To skoler kan ikke have samme navn i samme kommune.

### Ændrede fremmødelabels
For at gøre status tydeligere er labels ændret:
- "Ikke registreret" hedder nu "Tilmeldt"
- "Til stede" hedder nu "Uddannet"

---

## 23. januar 2026

### Advarsel ved overskridelse af pladser
Når en skole tilmelder flere deltagere end deres pladstildeling tillader, vises nu en advarsel på skoledetaljesiden. Dette gør det tydeligt hvornår der eventuelt skal sendes en tillægsfaktura.

### Sikker kursustilmelding
Kursustilmelding kræver nu login for at sikre at kun godkendte skoler kan tilmelde deltagere. Der er tre måder at logge ind:

1. **Adgangskode:** Skolen indtaster deres unikke kode (f.eks. `babe.dula.kibe.popy`)
2. **Direkte link:** Skolen bruger deres personlige tilmeldingslink som indeholder et token
3. **Personale-login:** Medarbejdere der er logget ind i admin kan tilmelde på vegne af alle skoler

Når en skole er logget ind, låses skole-dropdown til den pågældende skole. Personale ser et "Logget ind som..."-banner og kan frit vælge mellem alle skoler.

### Automatiske login-oplysninger
Når en skole tilmeldes Basal, genereres der automatisk en adgangskode og et direkte tilmeldingslink. Disse kan ses i en sammenklappelig login-sektion på skoledetaljesiden. Der er også en "Regenerer"-knap hvis skolen har brug for nye login-oplysninger (f.eks. hvis de er blevet delt ved en fejl).

### Email-notifikationer ved nye skoletilmeldinger
Medarbejdere kan nu vælge at modtage en email hver gang en ny skole tilmelder sig Basal. Indstillingen findes i brugerredigeringen under `/accounts/users/`.

### Permanent sletning af skoler
Der er nu mulighed for at slette en skole permanent via en "Slet permanent"-knap på skoledetaljesiden. Før sletning vises en oversigt over alt relateret data der vil blive slettet (personer, kursustilmeldinger, fakturaer osv.).

---

## 22. januar 2026

### Nyt Projektmål-dashboard
Nyt dashboard på `/projektmaal/` der giver overblik over projektets fremdrift i forhold til de fastsatte milepæle. Dashboardet viser:

- **Årlige mål og faktiske tal** for alle 5 projektår (2024/25 til 2028/29)
- **Farvekodning:** Grøn når målet er nået, rød når det ikke er
- **Måltal for:**
  - Nye skoler (nytilmeldte)
  - Forankringsskoler (skoler i andet år eller senere)
  - Antal kurser
  - Uddannede i alt og heraf lærere
  - Klasseforløb og elever (beregnes automatisk)

Under "Beregningsgrundlag" kan man justere antagelserne for beregning af klasseforløb og elever (f.eks. hvor mange klasseforløb en lærer gennemfører pr. år).

### Detaljeret tilmeldingsstatus
Skoler har nu en mere detaljeret tilmeldingsstatus der viser om de er:
- **Ikke tilmeldt** - aldrig været tilmeldt
- **Tilmeldt (ny)** - første år som tilmeldt
- **Tilmeldt (forankring)** - andet år eller senere
- **Frameldt** - tidligere tilmeldt, nu frameldt

### Kursuskapacitet med realtidsvalidering
Når man tilmelder deltagere til et kursus, tjekkes der nu i realtid om kurset har ledige pladser. Kursusdetaljer (dato, lokation, undervisere, ledige pladser) vises når man vælger et kursus.

### Underviser-markering på kursustilmelding
Der er tilføjet et felt til at markere om en deltager er underviser. Dette bruges til at skelne mellem lærere og andet personale i statistikken.

### Forklarende tekster ved filtrering
Når man filtrerer kurser eller tilmeldinger efter skoleår, vises nu en forklarende tekst øverst på siden, f.eks. "Viser kurser i skoleåret 2025/26" eller "Viser undervisere der deltog i kurser i skoleåret 2025/26".

---

## 21. januar 2026

### Tilmeld flere personer på én gang
Det er nu muligt at tilmelde flere deltagere til et kursus i én omgang. Klik på "Tilføj person" for at tilføje ekstra deltagerfelter. Hver deltager modtager sin egen bekræftelsesmail, og systemet tjekker automatisk om skolen har pladser nok til alle deltagere.

### Forbedret kontaktformular
Kontaktformularen er forbedret med:
- "Kontaktede de os?" er flyttet op over personvalg for bedre flow
- Ny "Nu"-knap der automatisk udfylder det aktuelle tidspunkt
- Dato forudfyldes automatisk med dagens dato

### Nye filtre på skolelisten
Skolelisten kan nu filtreres efter:
- **Tilmeldingsstatus:** Tilmeldt / Ikke tilmeldt / Frameldt
- **Kommune:** Vælg fra dropdown med alle kommuner
- **Ledige pladser:** Vis kun skoler med ubrugte pladser

### Nye kolonner på skolelisten
To nye kolonner giver bedre overblik:
- **Status:** Viser tilmeldingsstatus med farvede badges
- **Seneste henvendelse:** Dato for sidste kontakt med skolen

### Vælg kontaktperson fra liste
Når man registrerer en kontakt, vises nu checkboxes med alle personer tilknyttet den valgte skole. Der er også en "Anden (ikke på listen)"-mulighed hvis kontaktpersonen ikke er i systemet. Listen opdateres automatisk når man vælger en anden skole.

### Nye brugergrupper og rettighedsstyring
To nye brugergrupper gør det nemmere at tildele rettigheder:
- **Brugeradministrator:** Kan oprette og redigere brugere
- **Tilmeldingsadministrator:** Kan tilgå tilmeldingsadmin-sider og redigere tilmeldingsindhold

Brugerformularen er opdateret med checkboxes til at vælge grupper, så det er nemmere at se og ændre en brugers rettigheder.

### Nyt Tilmelding-menu
Der er tilføjet en ny dropdown-menu "Tilmelding" i topmenuen med direkte links til:
- Kursustilmelding (`/signup/course/`)
- Skoletilmelding (`/signup/school/`)

### Nulstilling af adgangskode
Administratorer kan nu nulstille andre brugeres adgangskoder. Brugeren modtager automatisk en email med den nye adgangskode.

### Forbedret skoleliste på dashboard
Skolelisten på dashboardet viser nu kommune i stedet for adresse, og skoler vises som "Skolenavn (Kommune)" i aktivitetslister for bedre overblik.

---

## 20. januar 2026

### Redigerbare tilmeldingssider
Tilmeldingssiderne kan nu redigeres via admin-panelet. For hver side kan man tilpasse:
- Overskrift og underoverskrift
- Intro-tekst over formularen (understøtter HTML)
- Tekst på tilmeld-knappen
- Overskrift og besked på successiden
- Om siden er aktiv (deaktiverede sider viser "tilmelding ikke mulig")

### Dynamiske formularfelter
Administratorer kan tilføje brugerdefinerede afkrydsningsfelter til tilmeldingsformularerne. Hvert felt kan have:
- En label-tekst (f.eks. "Jeg accepterer vilkår og betingelser")
- En hjælpetekst
- En vedhæftet fil som brugeren kan downloade (f.eks. et PDF-dokument med vilkår)
- Angivelse af om feltet er påkrævet

### Skoletilmelding med kommune-valg
Den nye skoletilmeldingsside på `/signup/school/` lader skoler tilmelde sig Basal. Først vælges kommune fra en dropdown, hvorefter systemet automatisk viser skoler i den pågældende kommune.

---

## 19. januar 2026

### Nyt tilmeldingssystem
Tilmeldingsstatus beregnes nu automatisk baseret på tilmeldings- og frameldingsdatoer. Dette gør systemet mere fleksibelt og giver mulighed for at se historik over tid.

### Framelding med dato
Skoler kan nu framelde sig permanent med en specifik dato. Dette bruges til skoler der ikke længere ønsker at deltage i Basal-projektet.

### Automatisk tilmeldingshistorik
Alle ændringer i tilmeldingsstatus spores automatisk og vises som en sammenklappelig sektion på skoledetaljesiden. Historikken viser hvornår skolen blev tilmeldt, eventuelle frameldinger, og hvem der foretog ændringerne.

### Oversigt over skoler uden faktura
Ny side der viser alle tilmeldte skoler som endnu ikke har modtaget en faktura for det aktuelle skoleår. Dette hjælper med at sikre at alle skoler bliver faktureret korrekt.

---

## 16. januar 2026

### Forbedret dashboard
Tilmeldingstabellen på dashboardet viser nu korrekt adresse, kommune og kontaktperson for hver skole.
