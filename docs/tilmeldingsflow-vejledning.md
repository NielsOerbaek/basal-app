# Vejledning: Tilmeldingsflow for skoler

Denne vejledning beskriver hvordan skoler tilmelder sig Basal og kurser, samt hvordan du kan hjælpe dem hvis de oplever problemer.

---

## 1. Skoletilmelding

### Sådan fungerer det

1. Skolen går til tilmeldingssiden og udfylder formularen med:
   - Kontaktpersonens navn, e-mail og telefon
   - Kommune
   - Valg af skole (fra liste) eller oprettelse af ny skole

2. Når de trykker "Tilmeld", sker følgende automatisk:
   - Skolen bliver registreret som tilmeldt
   - Der genereres en **adgangskode** og et **tilmeldingslink** til kursustilmelding
   - Kontaktpersonen modtager en bekræftelsesmail med disse oplysninger

3. På successiden får skolen besked om at de er tilmeldt, og kan gå direkte til kursustilmelding.

### Mulige problemer

| Problem | Årsag | Løsning |
|---------|-------|---------|
| "Skolen findes ikke på listen" | Skolen er ikke i systemet endnu | Skolen skal sætte flueben i "Min skole er ikke på listen" og indtaste skolens navn og adresse |
| Modtager ikke bekræftelsesmail | Forkert e-mail eller spam-filter | Tjek at e-mailen er korrekt. Bed dem kigge i spam/uønsket post. Du kan finde skolens oplysninger i systemet og sende dem manuelt |
| Skolen er allerede tilmeldt | En anden fra skolen har tilmeldt tidligere | Find skolen i systemet og del deres adgangskode, eller generer en ny under "Kodeord og tilmeldingslink" |

---

## 2. Kursustilmelding

### Sådan fungerer det

For at tilmelde sig kurser skal skolen først logge ind med enten:

- **Adgangskode**: Den kode de fik i velkomstmailen (f.eks. "bamo-kenu")
- **Direkte link**: Et personligt link med token der automatisk logger dem ind

Når de er logget ind:
1. Skolens navn vises og kan ikke ændres
2. De vælger et kursus fra dropdown-menuen
3. De tilføjer deltagere (navn, e-mail, evt. titel)
4. Hver deltager modtager en bekræftelsesmail

### Mulige problemer

| Problem | Årsag | Løsning |
|---------|-------|---------|
| "Ugyldig kode" | Forkert kode eller skolen er ikke tilmeldt | Tjek at skolen er tilmeldt i systemet. Find deres kode under skolens detaljer → "Kodeord og tilmeldingslink" |
| "Ugyldigt link" | Token i linket er forkert eller udløbet | Generer et nyt link til skolen via "Kodeord og tilmeldingslink" |
| Kan ikke vælge en anden skole | Det er meningen! Koden/linket låser til én skole | Hvis de skal tilmelde en anden skole, skal de bruge den anden skoles kode/link |
| Kursus vises ikke | Kurset er fuldt eller ikke aktivt | Tjek kursets kapacitet og status i systemet |
| Modtager ikke bekræftelsesmail | Forkert e-mail på deltager | Tjek deltagerens e-mail i tilmeldingen. Ret den og send bekræftelse manuelt hvis nødvendigt |

---

## 3. Administration af skolers adgang

### Find skolens loginoplysninger

1. Gå til skolens detaljeside
2. Under "Skoleoplysninger" klik på "Kodeord og tilmeldingslink"
3. Her kan du se og kopiere:
   - **Adgangskode**: Den kode skolen bruger til at logge ind
   - **Direkte link**: Et link der automatisk logger skolen ind

### Generer nye loginoplysninger

Hvis skolen har mistet deres kode, eller du vil give dem en ny:

1. Gå til skolens detaljeside
2. Klik på "Generer nye loginoplysninger"
3. Den gamle kode virker ikke længere
4. Send den nye kode/link til skolen

---

## 4. Typiske supporthenvendelser

### "Vi har glemt vores kode"
→ Find skolen i systemet og send dem deres kode eller generer en ny.

### "Vi vil tilmelde flere deltagere til samme kursus"
→ De kan bruge samme kode/link igen og tilføje nye deltagere.

### "Vi tilmeldte os ved en fejl / vil afmelde"
→ Find tilmeldingen under kurset og slet den, eller marker skolen som frameldt.

### "Vores kontaktperson er skiftet"
→ Opdater kontaktpersonen under skolens detaljer og generer evt. nye loginoplysninger.

### "Linket virker ikke"
→ Tjek at linket er komplet (det kan være afskåret i mailen). Alternativt send dem koden i stedet.
