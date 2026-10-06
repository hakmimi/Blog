---
title: "תמחור המודלים: מה דירוג שווה תחת רשימת מחירים להמחשה"
description: "סימולציה רטרוספקטיבית עם רשימת מחירים מוצהרת, קווי בסיס רלוונטיים ותקרת יכולת טיפול. מה המספרים אומרים, מה לא, ואיפה בחירת המודל ובחירת הסף חשובות."
series: "classification"
lang: "he"
order: 14
date: 2026-09-30
updated: 2026-10-04
keywords: ["רגישות לעלות", "סף החלטה", "יכולת טיפול", "ערך צפוי", "uplift", "קווי בסיס"]
readingTime: "11 דקות קריאה"
figure: "leaderboard-profit.png"
---

תחת רשימת המחירים להמחשה של הסדרה הזו, יצירת קשר עם כל רשומה בחלק ההשוואה הייתה *מפסידה* @@v:policy_baselines.csv|policy=call everyone|contribution|d@@ יחידות. הכלל "יוצרים קשר רק עם לקוחות שהקמפיין הקודם שלהם הצליח" מרוויח @@v:policy_baselines.csv|policy=prior-success rule|contribution|d@@ מ-@@v:policy_baselines.csv|policy=prior-success rule|records_selected|d@@ שיחות. מדיניות המודלים הטובות ביותר מרוויחות בערך פי שלושה. מה המספרים האלה אומרים, כמה שייך למודל וכמה לסף, ועד כמה אפשר להיות בטוחים?

<div class="callout">

**מטרה.** להפוך ציונים קפואים לתרומות מדומות מול קווי בסיס רלוונטיים, ולומר בדיוק מהי תרומה.

**תוכנית עבודה.** להצהיר על רשימת המחירים ועל מה שהסימולציה לא מודדת. להשוות מדיניות (סף נקודת איזון, סף ברירת מחדל, תקרת יכולת טיפול) עם קווי בסיס, לבדוק אם ההבדלים בין מודלים נראים, ולשנות את ערכה של הרשמה.

</div>

## מהו מספר תרומה

רשימת המחירים היא הנחה, לא של הבנק: שיחה עולה 1 והרשמה שווה 8. לכל קבוצת רשומות שנבחרו,

> תרומה = 8 × (הרשמות בין הרשומות שנבחרו) − 1 × (רשומות שנבחרו)

זו **סימולציית מדיניות רטרוספקטיבית**: היא סופרת כל הרשמה בין הרשומות שנבחרו כרווח, בין אם יצירת הקשר גרמה לה ובין אם לא.

| כמות | לכל רשומה שנוצר איתה קשר | צריכה |
|---|---|---|
| תרומה צפויה | V · p_contact − C | הסתברות להירשם כשיוצרים קשר |
| תרומה תוספתית | V · (p_contact − p_no_contact) − C | גם את ההסתברות *בלי* יצירת קשר |

כלל נקודת האיזון `p > C / V` (כאן 1/8) בא מהשורה הראשונה. הוא נכון אם אנשים לא היו נרשמים בלי יצירת הקשר, או אם ההסתברות הזו זהה לכולם. במערך הנתונים אין רשומות של אנשים שלא *נוצר* איתם קשר, ולכן הוא לא יכול לזהות את `p_no_contact`, ולא להפריד בין נטייה להגיב לבין **uplift**. הקמפיין ההיסטורי גם בחר למי להתקשר, ולכן הרשומות אינן מדגם של כל בסיס הלקוחות של הבנק, ורשימת המחירים מתעלמת מעלויות לא שוות, מיצירות קשר חוזרות ומלקוחות שאי אפשר להשיג. קראו כל מה שלמטה כדרך להשוות דירוגים ומדיניות בתנאים שווים.

## מדיניות וקווי בסיס

הציונים הם הקפואים מחלק 12 על 8,238 רשומות ההשוואה (928 מנויים). הספים נקבעים לפני הניקוד: ערך נקודת האיזון 1/8, ערך מחוץ-לקיפול מנתוני הפיתוח, ו-0.5 של הספרייה.

@@table:policy_baselines.csv|cols=policy,records_selected,contribution|fmt=records_selected:d;contribution:d|rename=policy:מדיניות,records_selected:רשומות שנבחרו,contribution:תרומה מדומה@@

בוחרים כל רשומה עם ציון של לפחות 1/8 ("random same size" בוחר אותו מספר רשומות באקראי, בממוצע על 400 הגרלות):

@@table:policy_by_model.csv|where=policy==break-even (1/8)|sort=contribution|desc|cols=model,records_selected,precision,recall,contribution,random_same_size,gain_vs_everyone,gain_vs_prior_rule|fmt=records_selected:d;precision:.3f;recall:.3f;contribution:d;random_same_size:d;gain_vs_everyone:d;gain_vs_prior_rule:d|rename=model:מודל,records_selected:נבחרו,precision:דיוק חיובי,recall:שלמות,contribution:תרומה,random_same_size:אקראי באותו גודל,gain_vs_everyone:רווח מול "מתקשרים לכולם",gain_vs_prior_rule:רווח מול כלל ההצלחה הקודמת@@

![תרומה מדומה של כל מודל בסף נקודת האיזון, עם נקודות הייחוס של "מתקשרים לכולם" וכלל ההצלחה הקודמת.](/series/classification/figures/leaderboard-profit.png)
*איור 1. אותם ציונים קפואים, רשימת מחירים אחת להמחשה.*

- **כל מודל מנצח את קווי הבסיס בהרבה.** בחירה אקראית באותו גודל מפסידה 130 עד 170 יחידות, ולכן הרווח לא בא מבחירת פחות רשומות. המודלים הטובים ביותר מרוויחים בערך 3,300 מול @@v:policy_baselines.csv|policy=prior-success rule|contribution|d@@ של כלל ההצלחה הקודמת, מפי חמישה עד שישה יותר רשומות.
- **הפיזור תלוי במי כוללים.** הטוב ביותר הוא @@v:policy_by_model.csv|model=Random forest|policy=break-even (1/8)|contribution|d@@ (יער אקראי), הנמוך מבין שנים-עשר @@v:policy_by_model.csv|model=Gaussian Naive Bayes|policy=break-even (1/8)|contribution|d@@ (Naive Bayes), הפרש של בערך 390. בלי Naive Bayes הנמוך הוא @@v:policy_by_model.csv|model=Decision tree|policy=break-even (1/8)|contribution|d@@ (עץ בודד), פיזור של בערך 215. רגרסיה לוגיסטית מרוויחה @@v:policy_by_model.csv|model=Logistic regression|policy=break-even (1/8)|contribution|d@@, בערך 94% מהטוב ביותר.
- **הסף חשוב.** בברירת המחדל של הספרייה, 0.5, אותם ציונים בוחרים רק כ-280 עד 370 רשומות (Naive Bayes, עם הסתברויות מנופחות, @@v:policy_by_model.csv|model=Gaussian Naive Bayes|policy=default cut-off 0.5|records_selected|d@@) ומרוויחים בערך 1,300 עד 1,600, כחצי ממדיניות נקודת האיזון:

@@table:policy_by_model.csv|where=policy==default cut-off 0.5|sort=contribution|desc|cols=model,records_selected,contribution|fmt=records_selected:d;contribution:d|rename=model:מודל,records_selected:נבחרו,contribution:תרומה@@

זה ספציפי למחירים האלה: סף צריך לבוא מהכלכלה ולהיבדק, לא להילקח מברירת מחדל.

**נסו בעצמכם.** הווידג'ט למטה מפעיל כל סף על הציונים הקפואים של חמישה מודלים. בחרו מודל, הזיזו את הסף, ושנו כמה הרשמה שווה: הקו המקווקו מסמן את סף נקודת האיזון `1/ערך` והנקודה הזהובה את הסף הטוב ביותר *במדגם הזה* (לא אופטימום של האוכלוסייה).

<div class="threshold-lab" data-lang="he" data-src="/series/classification/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/threshold-lab.js"></script>

## יכולת הטיפול היא תקרה

התייחסו ליכולת הטיפול כאל תקרה: יוצרים קשר לכל היותר עם k רשומות, הציונים הגבוהים קודם, ואף פעם לא עם אחת מתחת לסף נקודת האיזון. הקווים המלאים למטה שומרים על המגן הזה; צלבים מקווקוים ממלאים את היכולת בכל מקרה.

![תרומה מדומה מול יכולת טיפול לשלושה מודלים, עם מגן נקודת האיזון ובלעדיו.](/series/classification/figures/ch14-capacity.png)
*איור 2. מעבר לכ-1,500 שיחות, מילוי הרשימה מפסיד ערך אלא אם המגן עוצר אותו.*

@@table:policy_capacity.csv|where=model~LightGBM;Logistic regression;Random forest|where=break_even_guard==True|cols=model,capacity,records_selected,precision,recall,contribution,random_same_size|fmt=capacity:d;records_selected:d;precision:.3f;recall:.3f;contribution:d;random_same_size:d|rename=model:מודל,capacity:יכולת טיפול,records_selected:נבחרו,precision:דיוק חיובי,recall:שלמות,contribution:תרומה,random_same_size:אקראי באותו גודל@@

ב-200 שיחות שום דבר לא מפריד בין המודלים (976 עד 1,000). הפערים הגדולים ביותר הם ב-500 עד 1,000: ב-1,000 LightGBM מרוויח @@v:policy_capacity.csv|model=LightGBM|capacity=1000|break_even_guard=True|contribution|d@@ ורגרסיה לוגיסטית @@v:policy_capacity.csv|model=Logistic regression|capacity=1000|break_even_guard=True|contribution|d@@, בערך 8% יותר. בתקרה של 2,500 המדיניות עם המגן עוצרת בכ-1,400 עד 1,560 רשומות, בעוד שמילוי הרשימה מוריד את התרומה (LightGBM @@v:policy_capacity.csv|model=LightGBM|capacity=2500|break_even_guard=False|contribution|d@@ מול @@v:policy_capacity.csv|model=LightGBM|capacity=2500|break_even_guard=True|contribution|d@@).

## האם ההבדלים בין מודלים נראים?

תרומה של מדיניות היא סכום על רשומות, ולכן אפשר לעשות לה בוטסטראפ בזוגות כמו ל-AP בחלק 13, מותנה בציונים הקפואים ובספים. הפרשים מרגרסיה לוגיסטית תחת מדיניות נקודת האיזון, עם רווחי 95% שוליים וסימולטניים (אחת-עשרה השוואות בבת אחת):

@@table:policy_paired_bootstrap.csv|where=policy==break-even (1/8)|sort=diff|desc|cols=model,diff,ci95_lo,ci95_hi,simultaneous95_lo,simultaneous95_hi|fmt=diff:+,.0f;ci95_lo:+,.0f;ci95_hi:+,.0f;simultaneous95_lo:+,.0f;simultaneous95_hi:+,.0f|rename=model:מודל,diff:הפרש,ci95_lo:שולי נמוך,ci95_hi:שולי גבוה,simultaneous95_lo:סימולטני נמוך,simultaneous95_hi:סימולטני גבוה@@

היער האקראי, XGBoost, LightGBM, ה-booster של scikit-learn, CatBoost והרשת העצבית מרוויחים יותר מרגרסיה לוגיסטית עם רווחים סימולטניים מעל אפס. Extra trees, ה-SVM, k-NN והעץ הבודד אינם מופרדים ממנה, ו-Naive Bayes מרוויח פחות. היתרונות הנראים הם בערך 150 עד 200 יחידות ליער ול-boosters (ברשת העצבית בערך 80) על בסיס של כ-3,150, בערך 5% עד 6%. רווח שכולל אפס הוא חוסר ראיה להבדל, לא הוכחה לשוויון.

## כמה ההנחות חשובות?

הטבלה משאירה את העלות על 1, משנה את הערך, ומפעילה את סף נקודת האיזון 1/ערך על הציונים הגולמיים; "מתקשרים לכולם" מחושב מחדש לכל ערך.

@@table:policy_value_sensitivity.csv|where=model~LightGBM;Logistic regression;Gaussian Naive Bayes|cols=model,value,records_selected,contribution,call_everyone|fmt=value:d;records_selected:d;contribution:d;call_everyone:d|rename=model:מודל,value:ערך,records_selected:נבחרו,contribution:תרומה,call_everyone:מתקשרים לכולם@@

בערך של 4, "מתקשרים לכולם" מפסיד בגדול (@@v:policy_value_sensitivity.csv|model=LightGBM|value=4|call_everyone|d@@) והמודלים מרוויחים בערך 700 עד 1,050. בערך של 16, "מתקשרים לכולם" מרוויח @@v:policy_value_sensitivity.csv|model=LightGBM|value=16|call_everyone|d@@, והיתרון של המודלים עליו הוא רק בערך 1,100 עד 1,950: ככל שהצלחה שווה יותר, דירוג מוסיף פחות. סדר המודלים נשאר דומה בין ערכים, אבל *גודל* היתרון על קו בסיס טריוויאלי משתנה עם ההנחה, ולכן דווחו על היתרון על קו בסיס רלוונטי ליד הסך הכול והצהירו על המחירים.

## מודל פשוט או booster?

המדיניות הטובות ביותר מרוויחות כ-5% עד 6% יותר מרגרסיה לוגיסטית על 8,238 רשומות. אם זה מצדיק תהליך מורכב יותר תלוי בעובדות שמערך הנתונים הזה לא יכול לספק: כמה רשומות מדרגים, כמה טעות עולה בקנה מידה, באיזו תדירות צריך לאמן מחדש, מי מתחזק ומסביר. ראיות שהיו משנות את הבחירה: סט הערכה גדול או עדכני יותר, עלות שנמדדה לכל שיחה, מבחן פרוספקטיבי עם קבוצת ביקורת (כדי שאפשר יהיה להעריך uplift) ותוכנית ניטור (חלק 16). עד אז, התועלת של המודלים הטובים יותר נראית אבל צנועה, ורגרסיה לוגיסטית היא קו בסיס חזק.

## ניתוח ומסקנה: מה למדנו

- **תרומה היא סימולציה רטרוספקטיבית** תחת מחירים מונחים; היא לא מעריכה ערך שנוצר מיצירת קשר.
- **משווים לקווי בסיס רלוונטיים.** "לא מתקשרים לאף אחד", "מתקשרים לכולם", בחירה אקראית תואמת וכלל פשוט נותנים הקשר; כל שנים-עשר המודלים עוברים אותם בהרבה תחת המחירים האלה.
- **לוקחים את הסף מהכלכלה.** כאן סף נקודת האיזון בערך הכפיל את התרומה לעומת ברירת מחדל של 0.5, לכל מודל עם הסתברויות שמישות.
- **יכולת טיפול היא תקרה,** וההבדלים בין המודלים המובילים הם בערך 5% מהסך הכול ורגישים לערך המונח.

[חלק 15](/he/series/classification/15-inside-the-winner/) פותח את המודל שראיות הפיתוח היו בוחרות ושואל על מה הוא נשען ואיפה הוא נכשל.
