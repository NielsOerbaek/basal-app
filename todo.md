# Basal CRUD App

## Spørgsmål til teamet

- Ingen faktura i første år, men auto-fornyelse og faktura i starten af næste skoleår?
- Skal vi sende automatiske beskeder om at de er fornyet og at der er en faktura på vej?
  - For at undgå at sende fakturaer ud som de ikke har tænkt sig at betale.

## TODO


Kommune:
- Kommuner skal være en rigere datamodel med betalings information
  - Hvis der er kommuneaftale, gælder det så altid for alle skoler i kommunen, eller kun folkeskoler, eller kun nogen skoler?
    - KUN DEM HVOR DER ER KRYDS I KOMMUNEN BETALER
  - Skal det vises som mulighed når en skole tilmelder sig?
  - Skal faktisk efterligne skole-modellen ret meget.
  - Vise en liste over skoler i kommunen der har kommunen betaler

- Kursusdeltagere skal også kunne kobles på en kommune, og en kommune skal kunne have kontaktpersoner

- Gøre det tydeligt man kan tilmelde sig kursus i næste skoleår, hvis man er ny tilmeldt og snart er fortsætter

- Generelt email udsendings tool.
  - filter på skole tilmelding kommune
  - dry-run på modtagerliste
  - Send til mig som om jeg
  - preview vindue
  - Gem tidligere sendte mails.

  - Gøre det tydeligt at skolen er frameldt fra SKOLEÅR 
  - Trække liste af skoler som er med, og som ikke har frameldt sig i fremtiden.

- Sortering på skoler. 
  - Skoleår søger på match aktiv fra.
  - Vi vil gerne både kunne søge på Aktiv fra. 
  - Projekt mål gør det rigtigt
  - Gør filter mere tydelig og verbøs, så man forstår hvad man filtrerer på.

- Private og friskoler, efterskole. 
  - Ny status på skoler, alle nuværende er folkeskoler per default, men skal kunne ændres.
  - INSTITUTIONS_TYPE
  - Importér data
  - Fix bornholms frie *skole til privat skole.


  
### QA

- Fungerer emails som de skal? Kommer alle attachements med?

- Fungerer skoleår som de skal, og har vi overhovedet brug for skoleår?
- Hurtig løsning lavet på nye filter

- OBS skoler der tilmelder sig Basal efter sidste tilmeldingsfrist for skoleårets sidste kursus er ‘Ny skole’ i efterfølgende skoleår og bevarer sine 3 gratis kursuspladser. 

### Features

- Location på kurser skal være mere nuanceret og det kunne være smart at genbruge steder. Steder i deres egen tabel hvor man kan vælge eksisterende sted eller lave et nyt.
- Det samme for undervisere. Skal det være staff-brugere?
- Masseudsendelse af email til mange skoler (fx til alle ledere) + oprettelse af henvendelse
  - Hvad har de faktisk brug for?



### backup / export

- Export af alt data i ét excel ark


## Dataopgaver til basal eller studerende

- Gennemgang af alle skoler.
  - Registrere tilmeldinger til basal, også tilbage i tid.
  - Tjekke at kontaktoplysninger og antallet af pladser er korrekt
  - Tilføje ekstra information fra excel arket som kommentarer eller hendvendelser.

- Oprettelse af tidligere kurser
  - Oprette kurser med sted, tid og undervisere
  - Tilføje tidligere deltagere og match dem med skoler

- Tekst og dokumenter til signup-pages.


## Noter


