---
title: Basal — Brugervejledning
subtitle: De 10 mest almindelige arbejdsgange
author: Os & Data for Komiteen for Sundhedsoplysning
date: April 2026
lang: da
documentclass: article
geometry: a4paper, margin=2.2cm
fontsize: 11pt
toc: true
toc-depth: 2
---

\newpage

# Introduktion

Denne vejledning gennemgår de 10 mest almindelige arbejdsgange i **Basal**, det administrative system til Komiteen for Sundhedsopvlysnings Basal-projekt. Den er tænkt som et opslagsværk: hver arbejdsgang står for sig selv med en kort forklaring, trin-for-trin instruktion og et skærmbillede af den relevante side.

**Loginsiden** ligger på `{{LOGIN_URL}}`. Når du er logget ind, lander du på *Oversigt* (forsiden), som giver et hurtigt overblik over kommende kurser, seneste tilmeldinger og status på projektmålet for det aktuelle skoleår.

> 📸 *Skærmbillederne i denne vejledning er taget fra en demo-version af systemet. De skoler, kurser, navne og tal, du møder i skærmbillederne, er ikke rigtige data — i den faktiske produktionsversion vil du se jeres egne skoler og opdaterede tal.*

![Oversigt — den side du møder lige efter login](screenshots/01-dashboard.png)

\newpage

# 1. Find og filtrér skoler

**Hvad bruges det til?** At finde en bestemt skole eller danne et overblik over en delmængde af skoler — fx alle friskoler i Aarhus eller alle skoler, der er meldt ud.

Skoleoversigten er det centrale udgangspunkt for det meste arbejde med skoler. Du kan søge på navn, filtrere på kommune, institutionstype og tilmeldingsstatus, og åbne en hvilken som helst skole ved at klikke på dens navn.

**Sådan gør du:**

1. Klik på **Skoler** i topmenuen.
2. Brug søgefeltet til at søge på skolens navn, eller åbn filterknapperne over tabellen for at filtrere på kommune, institutionstype eller tilmeldingsstatus.
3. Klik på en skoles navn for at åbne dens detaljeside.
4. Brug knappen **Eksportér** (øverst til højre) hvis du vil have hele eller den filtrerede liste ud som Excel.

![Skoleoversigt med filtre og søgning](screenshots/02-skoleliste.png)

\newpage

# 2. Rediger skoleoplysninger og kontaktpersoner

**Hvad bruges det til?** At holde stamdata, EAN/CVR og kontaktpersoner ajour på en skole — særligt vigtigt fordi tilmelding til kurser kræver både EAN/CVR og en navngiven økonomisk ansvarlig.

På skolens detaljeside finder du alle oplysninger om skolen samlet ét sted: stamdata, kontaktpersoner, tilmeldingshistorik, kommentarer og filer.

**Sådan gør du:**

1. Åbn skolen fra skoleoversigten.
2. Klik på **Rediger** øverst til højre for at ændre stamdata (navn, adresse, kommune, institutionstype, EAN/CVR m.m.).
3. For at tilføje en kontaktperson, klik **+ Tilføj person** i feltet *Kontaktpersoner*. Sæt flueben ved *Koordinator* eller *Økonomisk ansvarlig*, hvis personen har en af de roller.
4. For at redigere en eksisterende person, klik blyant-ikonet ved siden af personen.

![Skolens detaljeside med stamdata, kontaktpersoner og handlinger](screenshots/03-skole-detalje.png)

![Redigeringsformular for skolens stamdata](screenshots/04-skole-rediger.png)

\newpage

# 3. Tilmeld eller afmeld en skole

**Hvad bruges det til?** At markere, hvornår en skole bliver del af Basal-projektet, eller at afmelde en skole, hvis den ønsker at trække sig.

Tilmeldingsstatus er afgørende for projektmålet og for, om skolen kan tilmelde sig kurser. En skole skal være *Tilmeldt* (have en tilmeldingsdato og ingen afmeldingsdato), før den kan bruge den offentlige tilmeldingsside.

**Sådan gør du:**

1. Åbn skolen fra skoleoversigten.
2. Klik **Tilmeldingsdatoer** eller knappen **Tilmeld**/**Afmeld** (øverst til højre eller i feltet *Tilmeldingsstatus*).
3. Indtast tilmeldingsdato (og evt. afmeldingsdato). Tilmeldingen registreres i skolens **historik**, så I kan se, hvornår den er sket.
4. Brug **Frasend Basal** for at give skolen adgang til den offentlige tilmeldingsside — det genererer en adgangskode og et token, som du finder under *Koder og links*.

\newpage

# 4. Tilføj kommentarer og filer på en skole

**Hvad bruges det til?** At dokumentere samtaler, aftaler og vedhæfte dokumenter (kontrakter, fakturaer, mails) på den enkelte skole, så historikken er samlet ét sted.

Kommentarer er datostemplet og signeret med dit navn. Filer kan downloades igen senere af enhver bruger med adgang.

**Sådan gør du:**

1. Åbn skolens detaljeside.
2. I feltet *Kommentarer*, klik **+ Tilføj kommentar**, skriv teksten og gem.
3. I feltet *Filer*, klik **Upload fil** og vælg dokumentet. Du kan tilføje en kort beskrivelse.
4. Både kommentarer og filer kan redigeres eller slettes via ikonerne ved siden af.

> 💡 *Genbrug skolens detaljeside (skærmbilledet i kapitel 2) som visuel reference.*

\newpage

# 5. Opret og offentliggør et kursus

**Hvad bruges det til?** At oprette et nyt kompetenceudviklingskursus, så skoler kan tilmelde sig via den offentlige tilmeldingsside.

Et kursus skal være **offentliggjort** (`is_published`) og have en gyldig **tilmeldingsfrist** for at kunne ses og vælges af skolerne.

**Sådan gør du:**

1. Klik **Kurser** i topmenuen → **+ Opret kursus**.
2. Udfyld titel/type, dato, sted (vælg eller opret en lokation), kapacitet, tilmeldingsfrist og undervisere.
3. Vedhæft eventuelt **kursusmateriale** (PDF) — det sendes automatisk med påmindelses-mailen.
4. Sæt flueben ved **Offentliggjort** og gem. Kurset dukker nu op i den offentlige tilmeldingsformular.

![Kursusoversigten viser alle kommende og afholdte kurser](screenshots/05-kursusliste.png)

![Formular til oprettelse af et nyt kursus](screenshots/06-kursus-opret.png)

\newpage

# 6. Håndtér kursustilmeldinger

**Hvad bruges det til?** At holde styr på, hvem der er tilmeldt et givet kursus — tilføje deltagere manuelt, rette skrivefejl, slette eller flytte tilmeldinger.

På kursets detaljeside ser du alle tilmeldte deltagere grupperet pr. skole, samt antal ledige pladser.

**Sådan gør du:**

1. Klik **Kurser** → vælg kurset.
2. På detaljesiden ser du alle tilmeldinger. Klik blyant-ikonet ved en deltager for at rette navn, e-mail, telefon eller stilling.
3. Klik **+ Tilføj tilmelding** for at oprette en deltager manuelt (fx hvis I tilmelder over telefon).
4. Brug **Bulk import** øverst på siden, hvis du har en hel liste, der skal ind på én gang.

![Detaljeside for et kursus med tilmeldte deltagere pr. skole](screenshots/07-kursus-detalje.png)

\newpage

# 7. Registrér fremmøde (roll call)

**Hvad bruges det til?** At markere, hvem der mødte op på selve kursusdagen. Bruges efterfølgende til projektmålet (antal uddannede undervisere) og til at sende relevant opfølgning.

Roll call-visningen er optimeret til at gå hurtigt igennem listen — én klik pr. deltager.

**Sådan gør du:**

1. Åbn kurset → klik **Fremmøde** (knappen ved siden af tilmeldingerne).
2. For hver deltager, klik **Mødt** eller **Ikke mødt**. Status gemmes automatisk.
3. Brug **Marker alle som mødt**, hvis I plejer at have næsten fuldt fremmøde og bare vil rette de få fraværende.
4. Når I er færdige, kan I gå tilbage til kursets detaljeside. Status vises også her.

![Roll call-visning til hurtig registrering af fremmøde](screenshots/08-rollcall.png)

\newpage

# 8. Send bulk-mail til skoler

**Hvad bruges det til?** At sende en e-mail til mange skoler på én gang — fx invitation til et nyt kursus, opfølgning på en kampagne, eller opdatering om Basal-projektet.

Bulk-mail-modulet understøtter modtagervalg ud fra rolle (koordinator, økonomisk ansvarlig, undervisere), filtrering på skoler/kommuner, og du kan se en preview før udsendelse.

**Sådan gør du:**

1. Klik **Masseudsendelse** i topmenuen → **+ Ny udsendelse**.
2. Vælg modtagere: skoler eller filter (kommune, institutionstype, tilmeldingsstatus), og hvilken rolle på skolen, der skal modtage mailen.
3. Skriv emne og brødtekst (du kan bruge skabeloner).
4. Klik **Preview** for at se, hvordan mailen ser ud, og hvor mange den sendes til.
5. Klik **Send** når du er klar. Bagefter kan du følge leveringsstatus i udsendelsens detaljeside og **gensende** evt. bouncede e-mails.

![Liste over tidligere bulk-udsendelser](screenshots/09-bulk-list.png)

![Formular til at oprette en ny bulk-udsendelse](screenshots/10-bulk-create.png)

![Detaljeside for en udsendelse med modtagere og leveringsstatus](screenshots/11-bulk-detalje.png)

\newpage

# 9. Projektmål og status

**Hvad bruges det til?** At se, hvor langt Basal-projektet er nået i forhold til de aftalte 5-årsmål: nye skoler, fortsættere, afholdte kurser, uddannede undervisere og elev-rækkevidde.

Projektmål-siden viser tal pr. skoleår med drill-down, så I kan klikke jer ind på en kategori og se, hvilke skoler/kurser tallet består af.

**Sådan gør du:**

1. Klik **Projektmål** i topmenuen (eller link fra forsiden).
2. Vælg det skoleår, du vil se (default er det aktuelle).
3. Klik på en af nøgletallene (fx *Nye skoler*) for at se de underliggende skoler.
4. Brug eksport-knappen, hvis du skal levere tallene videre i en rapport.

![Projektmål-siden med 5-årsmål og drill-down](screenshots/12-projektmaal.png)

\newpage

# 10. Aktivitetslog

**Hvad bruges det til?** At se, hvem der har ændret hvad og hvornår — fx hvis I undrer jer over, hvorfor en skole pludselig står som afmeldt, eller hvem der har redigeret en kontaktperson.

Aktivitetsloggen dækker oprettelser, opdateringer og sletninger på de vigtigste objekter (skoler, personer, kurser, tilmeldinger m.fl.) og kan filtreres på bruger, handling, objekttype og tidsrum.

**Sådan gør du:**

1. Klik **Aktivitet** i topmenuen.
2. Brug filtrene øverst (bruger, handling, objekttype, dato) til at indsnævre listen.
3. Klik på en aktivitet for at se de konkrete felter, der blev ændret (gammel og ny værdi).
4. Fra en skole eller et kursus kan du også åbne en filtreret aktivitetslog kun for det objekt — link i feltet *Seneste aktivitet*.

![Aktivitetslog med filtre og detaljeret historik](screenshots/13-aktivitetslog.png)

\newpage

# Hvis noget ikke virker

- **En skole kan ikke tilmelde sig et kursus**: Tjek, at skolen har både EAN/CVR-nummer (eller "kommunen betaler" markeret) **og** en kontaktperson markeret som *Økonomisk ansvarlig*. Begge dele kræves.
- **En e-mail er bouncet**: Du kan se bouncede mails som røde markeringer ved e-mail-adresser. Ret e-mailen på personen, og afsendelsesstatus nulstilles automatisk.
- **Du har brug for at se, hvad en kollega har lavet**: Brug aktivitetsloggen (kapitel 10) — alle ændringer er logget.
- **Spørgsmål til systemet**: Tag fat i Esther Chemnitz (`ech@sundkom.dk`) eller skriv til `basal@sundkom.dk`.
