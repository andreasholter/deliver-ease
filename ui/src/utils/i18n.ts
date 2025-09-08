// ui/src/utils/i18n.ts
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { en } from "./translations.en";
import { no } from "./translations.no";
import { sv } from "./translations.sv";
import { da } from "./translations.da";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: {
        translation: en,
      },
      no: {
        translation: no,
      },
      sv: {
        translation: sv,
      },
      da: {
        translation: da,
      },
    },
    fallbackLng: "no",
    debug: true,
    interpolation: {
      escapeValue: false, // not needed for react as it escapes by default
    },
    detection: {
      order: ['queryString', 'cookie', 'localStorage', 'navigator', 'htmlTag'],
      caches: ['cookie'],
      lookupQuerystring: 'lang',
    }
  });

export default i18n;
