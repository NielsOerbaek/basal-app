# Ændringer

Oversigt over nye funktioner og ændringer i Basal-systemet, siden 16. januar 2026

---

## 13. april 2026

### "Ønsker ikke at blive kontaktet" på skoler
Skoler kan nu markeres med "Ønsker ikke at blive kontaktet" via et flueben på skolesiden. Skoler med denne markering undtages automatisk fra masseudsendelser. Ved test-kørsel og afsendelse vises hvor mange skoler der er undtaget.

---

## 9. april 2026

### Kursusdeltagere kan tilknyttes til kommune (OSO-235)
Kursusdeltagere kan nu tilknyttes direkte til en kommune, hvis de er ansat i kommunen (og ikke på en skole). På kommunesiden vises alle deltagere fra kommunen samlet.

- På **tilmeldings-formularen** (Tilføj/redigér tilmelding) vælges tilknytning via radioknapper øverst: *Skole*, *Kommune* eller *Anden organisation*. Kun det relevante felt vises ad gangen, og de andre nulstilles automatisk ved gem.
- På **kommune-detaljesiden** er der en ny sammenklappelig sektion **"Kursusdeltagere fra kommunen (N)"** der viser alle deltagere tilknyttet kommunen, grupperet efter kursus.
- Kommune-detaljesidens skoletabel er nu sorterbar (navn, type, status, aktiv fra, brugte pladser) og har fået en **Type**-kolonne magen til oversigten på Skoler-siden. Den bruger samme tabel som /skoler, så visningen er konsistent.
- På **kursus-detaljesiden** hedder kolonnen "Skole" nu **"Skole/kommune/organisation"** og viser kommunenavnet som link, hvis deltageren er tilknyttet en kommune.
- Listen over de 98 danske kommuner findes nu som et fast opslagsværk i systemet, så dropdown'en er ens overalt. En enkelt stavefejl ("Vesthimmerland" → "Vesthimmerlands") er samtidig rettet.

---

## 7. april 2026

### Faktureringsoplysninger deles på kommuneniveau (OSO-164)
Når flere skoler i samme kommune har **"Kommunen betaler"** slået til, deler de nu faktureringsoplysningerne. Det betyder at man kun skal taste adresse, EAN, kontaktperson og e-mail én gang for fx Fredensborg eller Bornholms Regionskommune — ændringer slår automatisk igennem på alle skolerne.

- På kommune-detaljesiden er der øverst tilføjet en sektion **"Faktureringsoplysninger for kommunen"**, hvor oplysningerne kan redigeres centralt. Sektionen vises kun, hvis mindst én skole i kommunen har "Kommunen betaler" slået til.
- På skolens redigeringsside vises en notits om at oplysningerne deles, så man ikke ved et uheld kommer til at ændre dem for én skole alene.
- På skolens detaljeside vises et lille mærke **"deles med kommunen"** ved siden af "Kommunen betaler", så det er tydeligt hvor oplysningerne kommer fra.
- Hvis fakturerings-e-mailen bouncer, vises advarslen automatisk på alle skolerne i kommunen.
- Eksisterende data er flyttet automatisk: Bornholms Regionskommune og Fredensborg Kommune (de to kommuner der i dag har "Kommunen betaler" aktiveret) har fået deres faktureringsoplysninger samlet på kommuneniveau.

### Brugermanual i systemet
Der er tilføjet en **Brugermanual** under brugermenuen øverst til højre. Manualen gennemgår de 10 mest almindelige arbejdsgange (find skoler, rediger kontaktpersoner, opret kurser, registrér fremmøde, send bulk-mail m.fl.) med skærmbilleder og trin-for-trin vejledninger.

### Krav om økonomisk ansvarlig før kursustilmelding (OSO-234)
En skole kan nu kun tilmelde sig et kursus, hvis der er udfyldt en økonomisk ansvarlig på skolen. Hvis feltet mangler, vises en advarsel på tilmeldingssiden med link til skolens side, og tilmeld-knappen er deaktiveret — på samme måde som med EAN/CVR-nummer.

### Friskoler og efterskoler i databasen (OSO-176, OSO-178, OSO-180)
Alle frie/private grundskoler og efterskoler, der dækker 7.-10. klasse, er nu importeret fra STIL's institutionsregister.

- Skoler har nu en **institutionstype** (Folkeskole, Fri/privat grundskole, Efterskole), der vises på skolens detaljeside og kan redigeres på skolens redigeringsside.
- Skoleoversigten viser institutionstype som en farvet chip i sin egen kolonne, og der er tilføjet et nyt **filter** så man kan vise kun folkeskoler, friskoler eller efterskoler.
- Excel-eksporten af skoleoversigten inkluderer nu institutionstype.
- For nye importerede skoler er skolelederen oprettet som en kontaktperson, og skolens generelle e-mail er oprettet som "Generel Kontakt".
- Skoler der både er friskole og efterskole (samme fysiske institution) markeres som **"Kombineret fri-/efterskole"** og dukker op både når man filtrerer på friskoler og når man filtrerer på efterskoler.

---

## 26. marts 2026

### Kursustilmelding: duplikeret dato fjernet (OSO-231)
Datoen blev vist to gange i dropdown-menuen ved kursustilmelding. Nu vises den kun én gang.

### Bounce-håndtering i databasen
Når en e-mail bouncer, markeres e-mailadressen nu som bouncet i databasen (på kontaktpersoner, kursustilmeldte og faktureringskontakter). Markeringen fjernes automatisk hvis e-mailadressen ændres.

### Bounce-advarsler på alle e-mailadresser
En gul advarselsikon vises ved bouncede e-mailadresser overalt i systemet: skolesiden, den offentlige skoleside, kommuneoversigt, oversigten og kursus-fremmødelisten. Ikonet har en tooltip med dato for bounce.

### Masseudsendelse: bounce-overblik og gensendelse
Detaljesiden for en masseudsendelse viser nu:
- Antal e-mails der ikke kunne leveres og antal skoler der mangler
- Klik på "Skoler mangler" for at se hvilke skoler det drejer sig om
- Mulighed for at gensende en e-mail til en ny adresse, med valg om at opdatere kontaktpersonens e-mail permanent
- Hvis kontaktpersonens e-mail er opdateret siden bouncen, vises den nye adresse i gensend-dialogen
- Skolenavne i tabellen linker nu til skolens detaljeside
- Tabellen kan sorteres efter skole og status
- E-mailens indhold er nu sammenklappet som standard

---

## 24. marts 2026

### Billeder i e-mails virker nu
Billeder indsat via skabelonerne (Summernote) havde relative stier, som ikke kunne vises i e-mail-klienter. De konverteres nu automatisk til absolutte URL'er.

### Deltagerliste i koordinator-bekræftelsesmail
Deltagerlisten i koordinatorens bekræftelsesmail vises nu korrekt som formateret HTML (den blev tidligere vist som rå HTML-kode). Listen inkluderer nu også titel og underviser-markering.

### Afsender på e-mails ændret
E-mails sendes nu fra `basal@raakode.dk` i stedet for `niels@raakode.dk`.

### Bounce-notifikationer (OSO-229)
Når en e-mail ikke kan leveres (bounce) eller markeres som spam, sendes en notifikation til `basal@sundkom.dk` med information om modtager, tilknyttet person, skole og rolle.

### Masseudsendelse: bedre filtertæller
Filtertælleren viser nu antal skoler der matcher filteret, antal skoler der sendes til, antal email-adresser, og antal skoler der springes over.

### Masseudsendelse: filterfejl rettet
Statusfiltrene "Alle tilmeldte" og "Alle ikke-tilmeldte" med skoleår virkede ikke korrekt i masseudsendelse — de returnerede alle skoler i stedet for de filtrerede. Filtreringslogikken er nu samlet ét sted så den virker ens på skolelisten og i masseudsendelse.

### Kurser med overskredet tilmeldingsfrist skjules
Kurser hvor tilmeldingsfristen er overskredet vises ikke længere på tilmeldingssiden.

### Rate limit ved kursuspåmindelser
Der er tilføjet en forsinkelse mellem afsendelse af kursuspåmindelser for at undgå Resends rate limit.

---

## 20. marts 2026

### Nyt domæne: db.sammenomtrivsel.com
Produktionsmiljøet er nu tilgængeligt på db.sammenomtrivsel.com.

### Samarbejdsvilkår og login-oplysninger på skolernes side
Samarbejdsvilkår (PDF) og login-oplysninger til sammenomtrivsel.com kan nu redigeres ét centralt sted i admin (Projektindstillinger) og vises automatisk på alle tilmeldte skolers sider.

### Dokumenter gemmes ikke længere på skolen ved tilmelding
Dokumenter fra tilmeldingsformularen sendes stadig med i bekræftelsesmailen, men gemmes ikke længere som filer på den enkelte skole.

### Bekræftelsesmail til koordinator ved kursustilmelding (OSO-207, OSO-208)
Koordinatoren modtager nu en separat bekræftelsesmail med liste over tilmeldte deltagere, når nogen tilmelder sig et kursus. Ved skoletilmelding sendes bekræftelsesmailen til både koordinator og økonomisk ansvarlig.

### Flere modtagertyper ved masseudsendelse (OSO-204, OSO-206)
Masseudsendelse understøtter nu fem modtagertyper: Koordinator, Økonomiansvarlig, Koordinator + Økonomiansvarlig, Første kontakt og Alle kontakter. Det gør det muligt at sende til skoler, der ikke har en koordinator eller økonomiansvarlig.

### E-mail-skabeloner viser korrekte variabler (OSO-88)
Admin viser nu de rigtige tilgængelige variabler for hver e-mail-type, så man kan se hvilke felter der kan bruges i skoletilmeldings- vs. kursustilmeldingsbekræftelser.

### Tilmeldingshistorik vises korrekt på skolernes side (OSO-192)
Datoer i tilmeldingshistorikken på skolernes offentlige side vises nu korrekt.

### Henvendelser er fjernet (OSO-205)
Funktionen "Henvendelser" er fjernet fra systemet. Henvendelser registreres fremover som kommentarer på den enkelte skole.

### Ændringer i skoletilmeldingsformularen (OSO-211)
Labels og felter i skoletilmeldingsformularen er opdateret. Kommentarfeltet er fjernet.

### Pladsinformation kan slås fra (OSO-194)
Pladsinformation på kursustilmeldingssiden kan nu slås til/fra i Projektindstillinger.

### Øvrige rettelser
- EAN-felter omdøbt til "EAN/CVR-nummer" (OSO-181)
- "Login til app" omdøbt til "Login til www.sammenomtrivsel.com" (OSO-172)
- Tilmeldingsfrist hjælpetekst rettet fra 5 til 6 uger (OSO-216)

---

## 18. marts 2026

### Samarbejdsvilkår vedhæftes bekræftelsesmail
Når en skole tilmelder sig, vedhæftes dokumenter fra tilmeldingsformularen (f.eks. samarbejdsvilkår-PDF) automatisk til bekræftelsesmailen.

### EAN/CVR-nummer kræves ved kursustilmelding
Skoler skal nu have udfyldt EAN/CVR-nummer, før de kan tilmelde sig et kursus. Hvis nummeret mangler, vises en advarsel med link til skolens side, og tilmeldingsknappen er deaktiveret. Undtaget er skoler, hvor kommunen betaler.

### Link til skoletilmelding på kursustilmeldingssiden
Kursustilmeldingssiden har nu et link "Ikke tilmeldt endnu? Tilmeld din skole til Basal" i bunden, så skoler der ikke er tilmeldt nemt kan finde tilmeldingssiden.

### Samarbejdsvilkår ved skoletilmelding
Skoletilmeldingsformularen understøtter nu accept af samarbejdsvilkår via et afkrydsningsfelt med vedhæftet PDF (konfigureres i admin).

### Dokumenter synlige på skolernes side
Skolernes offentlige side viser nu en "Dokumenter"-sektion med filer tilknyttet skolen (f.eks. samarbejdsvilkår). Dokumenterne kan downloades direkte.

### Nyt forbrugsoverblik på skolernes side

Kursuspladser-oversigten på skolernes side er redesignet. Den hedder nu "Forbrug af kursuspladser" og viser en samlet oversigt over forbrug og priser pr. skoleår. Hvert skoleår er et sammenfoldeligt afsnit med oplysninger om medlemskab, gratis pladser, forankringsplads og tilkøbte pladser med automatisk prisberegning. Det igangværende skoleår er udfoldet som standard. Forankringspladsblokken viser om den gratis forankringsplads er brugt eller ej.

### Fakturamodulet er fjernet
Fakturaregistrering i databasen er fjernet. Fakturering håndteres fremover uden for databasen.

### Notifikationsmail ved kursustilmelding
Basal modtager nu en automatisk mail, når en skole tilmelder sig et kursus. Mailen indeholder skolens navn, kursus, deltagere, økonomisk ansvarlig, EAN/CVR-nummer og beregnet fakturabeløb (gratis eller tilkøbspris).

### Tilmeld til kursus åbner nu i nyt vindue
Knappen "Tilmeld til kursus" på skolernes egen side åbner nu tilmeldingssiden i et nyt vindue.

### EAN-advarsel vises ikke længere når kommunen betaler
Advarslen om manglende EAN-nummer vises ikke, hvis skolen er markeret som kommunalt betalt.

### Advarsel om overskridelse af kursuspladser er fjernet
Advarslen "Skolen bruger flere pladser end tildelt" er fjernet fra skolesiden.

### Automatisk tilmeldingsfrist ændret til 6 uger
Standard tilmeldingsfrist sættes nu til 6 uger før kursusstart (tidligere 5 uger).

### Tekstrettelser
- EAN-nummer omdøbt til EAN/CVR-nummer
- Hjælpetekst ved EAN-felt på tilmeldingssiden opdateret til "evt. fremtidig fakturering"
- Tekst ved underviser-felt på kursustilmelding præciseret

### Skolelisten har fået en ny filterpanel
Filterpanelet i skolelisten er omdesignet: det er nu skjult som standard og kan foldes ud. Når filtre er aktive, vises en kort dansk opsummering i stedet for de individuelle filterfelter. Filteret tager nu hensyn til det valgte skoleår, så fx status (tilmeldt/frameldt/afventer) vurderes i forhold til det pågældende skoleår frem for det nuværende.

### Skoler der har frameldt sig tæller nu med i "fortsætter"-filteret
Skoler der er frameldt i løbet af et skoleår medtages nu korrekt i filteret for fortsættende skoler i det pågældende år.

---

## 11. marts 2026

### Aktivitetsloggen kan nu filtreres på dato og medarbejder
Aktivitetsloggen (/aktivitet) har fået nye filtre: dato-interval (fra/til) og medarbejder. Alle filtre kan kombineres og bevares ved sideskift.

### Afmeldelsesdato kan nu rettes
Hvis en skole er frameldt med en forkert dato, kan datoen nu rettes via en redigeringsknap på skolens detaljeside. Detaljesiden viser nu også tilmeldingsdatoer og "Frameldt d." for frameldte skoler.

### Tilmeldingshistorik med farvede chips og mulighed for at slette
Tilmeldingshistorikken viser nu tilmeldings- og frameldingshændelser med farvede chips (grøn for Tilmeldt, rød for Frameldt). Datoerne afspejler altid de aktuelle værdier, også efter rettelser. Hver række kan slettes hvis der er fejl (fx ved utilsigtet framelding og gentilmelding).

### Kolonneoverskrift "Tilmeldt skoleår" omdøbt til "Aktiv fra"
I skolelisten er kolonneoverskriften ændret fra "Tilmeldt skoleår" til "Aktiv fra" for at matche det faktiske indhold.

### Ny/fortsætter-status baseret på "aktiv fra" i stedet for tilmeldingsdato
Projektmål-siden og forsiden viser nu ny/fortsætter-status for skoler baseret på "aktiv fra"-datoen i stedet for tilmeldingsdatoen. Det betyder at en skole er "ny" i det skoleår hvor "aktiv fra" falder, og "fortsætter" i de efterfølgende år. Samme rettelse er lavet i faktura-oversigten.

### Projektmål viser nu også det kommende skoleår
Projektmål-siden viser nu tal for det kommende skoleår (fx skoler der allerede har tilmeldt sig), i stedet for kun at vise måltal.

---

## 20. februar 2026

### Rediger og slet kommentarer på skolesiden
Staff kan nu redigere kommentarer på skolesiden via en ny redigeringsknap (blyant-ikon) ved siden af sletteknappen.

---

## 16. februar 2026

### Kodeord og tilmeldingsknap på skolens side
Skolens offentlige side viser nu kodeordet under "Kodeord og links" (med vis/skjul og kopiér), samt en "Tilmeld til kursus"-knap der linker direkte til kursustilmeldingen.

### Skoleår-dropdown går nu tilbage til 2022/23
Dropdown'en for "Aktiv fra (skoleår)" på tilmeldingsdato-siden viser nu alle skoleår fra 2022/23 og frem, i stedet for kun 5 år fra tilmeldingsdatoen.

---

## 13. februar 2026

### "Forankring" omdøbt til "Fortsætter"
Alle steder i systemet hvor der stod "forankring" eller "forankringsplads" er nu ændret til "fortsætter" og "fortsætterplads". Dette gælder skolelisten, skoledetaljer, skolens side, dashboard, projektmål, tilmeldingssiden og faktura-oversigten.

### Advarsel om synlig kommentar på personredigering
Når man redigerer en kontaktperson i staff-viewet, vises nu en advarsel om at kommentarfeltet også er synligt på skolens side. Fortrolige bemærkninger bør i stedet tilføjes som en kommentar på skolen.

### Email-domænebegrænsning på dev
Dev-miljøet kan nu kun sende emails til osogdata.dk, raakode.dk og sundkom.dk. Dette forhindrer at rigtige brugere ved en fejl modtager emails fra dev-serveren.

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
