# Changelog

## 2026-04-10

- Canviades les rutes públiques dels serveis al català:
  - `/albumes-fotograficos` -> `/albums-fotografics`
  - `/marcos-a-medida` -> `/marcs-a-mida`
  - `/impresion-lienzos` -> `/impressio-llencos`
  - `/impresion-hahnemuhle` -> `/impressio-hahnemuhle`
  - `/sobre` -> `/qui-som`
  - `/calculadora` -> `/area-professional`
- Afegides redireccions permanents HTTP 301 de les rutes antigues cap a les noves.
- Mantinguts els endpoints interns de Flask per no afectar la lògica existent ni les referències amb `url_for(...)`.
- El `sitemap.xml` queda actualitzat automàticament perquè es genera a partir dels endpoints actuals.
- Verificat que el selector de llengua `/lang/<code>` no es modifica.
