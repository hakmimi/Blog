---
title: "כשהזמן שובר את המודל: מאמנים על העבר ומחליטים על העתיד"
description: "מאמנים על 80% הראשונים של הקובץ ומדרגים את ה-20% האחרונים, שבהם חלקם של המנויים קופץ מ-6.4% ל-30.8%. כל בחירה נשארת בתוך העבר; משווים תיקונים שאפשר להפעיל ותיקון אחד שאי אפשר, ואז מתארים איך מפעילים מדיניות כזו באמת."
series: "classification"
lang: "he"
order: 16
date: 2026-09-30
updated: 2026-10-04
keywords: ["סחיפת התפלגות", "prior shift", "אימות בזמן", "concept drift", "ניטור", "פריסה"]
readingTime: "14 דקות קריאה"
figure: "ch16-time-shift.png"
---

מאמנים על 80% הראשונים של הקובץ, ו-@@j:temporal_shift.json|prevalence_past|.1%@@ מרשומות האימון הן מנויים. מדרגים את ה-20% האחרונים, והחלק הוא @@j:temporal_shift.json|prevalence_future|.1%@@. תחת המחירים להמחשה, יצירת קשר עם *כל* רשומה בבלוק האחרון הזה מרוויחה @@v:temporal_policies.csv|model=LightGBM|correction=none|policy=break-even (1/8)|call_everyone|d@@ יחידות. לכן השאלה אינה רק "איזה מודל מדרג הכי טוב על רשומות מאוחרות?" אלא "מה מודל מוסיף לקו בסיס שכבר חזק?"

<div class="callout">

**מטרה.** להעריך מודלים כמו שישתמשו בהם, על רשומות שבאות אחרי נתוני האימון שלהם.

**תוכנית עבודה.** לחתוך את הקובץ לפי סדר השורות ולשמור כל בחירה בתוך העבר. לאבחן מה השתנה. להשוות מודלים ותיקונים בתוך בלוק העתיד ומול "מתקשרים לכולם". ואז לתאר איך בודקים, מנטרים ומתחזקים מדיניות כזו.

</div>

## התכנון

בקובץ אין תאריכים, ולכן **מיקום השורה משמש כתחליף לזמן**: 80% הראשונים של השורות הם ה*עבר*, ה-20% האחרונים ה*עתיד*. ההגדרות נבחרות עם **קיפולים בחלון מתרחב** בתוך העבר (מאמנים על כל מה שלפני בלוק ומאמתים על הבא).

@@table:temporal_blocks.csv|cols=block,first_row,last_row,records,positives,prevalence|fmt=first_row:d;last_row:d;records:d;positives:d;prevalence:.3f|rename=block:בלוק,first_row:שורה ראשונה,last_row:שורה אחרונה,records:רשומות,positives:חיוביים,prevalence:שכיחות@@

השכיחות כבר נסחפת בתוך העבר (5.9% עד 13.8%), ולכן AP מושווה *בתוך* בלוק, אף פעם לא בין בלוקים. המודלים ומרחבי החיפוש הם של חלק 12, עם מועמדים שמדורגים לפי AP ממוצע על שלושת בלוקי האימות, עצירה מוקדמת על 10% אקראיים מנתוני האימון (עדיין העבר), ומדיניות סף אחת שנבחרה על חיזויי בלוקי האימות. ה-SVM עם Platt scaling מושמט כי קיפולי הכיול שלו היו צריכים תכנון מסודר. בלוק העתיד מדורג פעם אחת.

![חלקם של המנויים בכל בלוק אימות בזמן ובבלוק העתיד, עם ספירות רשומות.](/series/classification/figures/ch16-folds.png)
*איור 1. הבלוקים נבדלים בשכיחות אפילו בתוך העבר.*

## מה השתנה?

"הנתונים השתנו" יכול לפרש דברים שונים עם תרופות שונות. **השכיחות** עלתה מ-@@j:temporal_shift.json|prevalence_past|.1%@@ ל-@@j:temporal_shift.json|prevalence_future|.1%@@. **הקלטים** זזו: עמודות המקרו רחוקות כמה סטיות תקן מערכי העבר שלהן, ומסווג שמבחין בין עבר לעתיד רק לפי הקלטים מקבל AUC של @@j:temporal_shift.json|domain_classifier_auc_past_vs_future|.4f@@.

@@table:temporal_covariate_shift.csv|rename=standardised_difference:העתיד פחות העבר בסטיות תקן מאוחדות@@

ייתכן ש**הקשר בין הקלטים לתוצאה** השתנה גם הוא, אבל אנחנו לא יכולים לראות אותו, כי שניהם זזו יחד. תיקון של **prior shift (הסחף בתוויות)** מניח משהו צר בהרבה: שהתפלגויות הקלט *בתוך כל מחלקה* יציבות ורק פרופורציות המחלקות זזות. ההפרדה כמעט המושלמת למעלה היא ראיה נגד זה.

## דירוג בתוך בלוק העתיד

כל ההשוואות כאן משתמשות באותן 8,238 רשומות עתיד. דירוג אקראי מקבל את השכיחות, @@j:temporal_shift.json|prevalence_future|.3f@@. אל תשוו את ה-AP האלה לאלה של חלק 12: AP תלוי בשכיחות, שעכשיו גבוהה פי חמישה.

@@table:temporal_policies.csv|where=policy==break-even (1/8)|where=correction==none|sort=ap|desc|cols=model,ap,roc_auc,mean_score,ece_10_quantile|fmt=ap:.3f;roc_auc:.3f;mean_score:.3f;ece_10_quantile:.3f|rename=model:מודל,ap:AP,roc_auc:AUC,mean_score:ציון ממוצע,ece_10_quantile:ECE@@

![שמאל: דיוק ממוצע על בלוק העתיד. ימין: תרומה מדומה בנקודת האיזון 1/8 לכל מודל עם כל תיקון; הקו המקווקו הוא "מתקשרים לכולם".](/series/classification/figures/ch16-time-shift.png)
*איור 2. אותם מודלים, אותן רשומות עתיד.*

הסדר אינו זה של החלוקה האקראית: extra trees, k-NN, CatBoost והיער האקראי מובילים ב-AP; רגרסיה לוגיסטית באמצע; וה-booster של scikit-learn, LightGBM, העץ הבודד ו-XGBoost אחרונים, עם XGBoost, העץ הבודד ורגרסיה לוגיסטית נמוכים ביותר ב-AUC. זה בלוק עתיד אחד בלי רווח, ולכן אל תקראו הפרשים של כמה מאיות כסדר. הנקודה העמידה היא ש**המובילים בהשוואה על חלוקה אקראית אינם מובטחים להוביל על רשומות מאוחרות**, ושציונים ממוצעים (בערך @@v:temporal_policies.csv|model=LightGBM|correction=none|policy=break-even (1/8)|mean_score|.2f@@ ל-LightGBM) יושבים הרבה מתחת לשיעור האמיתי: הציונים שייכים לעבר.

## מה תיקון יכול ומה לא

תחת הנחה של label shift, אפשר לשקלל מחדש את ההסתברויות של מודל על ידי הכפלת הסיכויים ביחס בין הסיכויים הקודמים החדשים לישנים. תיקון מונוטוני לא יכול לשנות AP או AUC; הוא משנה *מי חוצה את הסף*. מנסים ארבעה prior-ים, שלושה מהם זמינים ברגע ההחלטה:

| תיקון | prior שמשתמשים בו | זמין ברגע ההחלטה? |
|---|---|---|
| ללא | שכיחות העבר | כן |
| החלון האחרון | שכיחות בלוק האימות האחרון (@@j:temporal_shift.json|prevalence_last_validation_block|.1%@@) | כן: אומדן מאחר |
| EM | מוערך רק מהציונים של בלוק העתיד (Saerens, Latinne ו-Decaestecker, 2002) | עקרונית: לא צריך תוויות, אבל מניח label shift וציונים מכוילים |
| אורקל | השכיחות האמיתית של העתיד (@@j:temporal_shift.json|prevalence_future|.1%@@) | **לא**: אבחון בלבד |

תרומה מדומה בסף נקודת האיזון 1/8:

@@table:temporal_policies.csv|where=policy==break-even (1/8)|pivot=model:correction:contribution|fmt=none:d;last-window prevalence:d;EM on unlabelled scores:d;oracle prevalence (diagnostic):d|rename=model:מודל,none:ללא,last-window prevalence:חלון אחרון,EM on unlabelled scores:EM,oracle prevalence (diagnostic):אורקל (לא ניתן לפריסה)@@

קנה המידה הוא **"מתקשרים לכולם", @@v:temporal_policies.csv|model=LightGBM|correction=none|policy=break-even (1/8)|call_everyone|d@@**.

**נסו בעצמכם.** בחרו מודל, ואז ספרו לו שיעור בסיס עם המחוון או הכפתורים (תקופת האימון, בלוק האימות האחרון, אומדן ה-EM, האורקל). הווידג'ט מראה כמה רשומות חוצות את הסף, את התרומה המדומה ואת הרווח על "מתקשרים לכולם". הדירוג אף פעם לא משתנה; רק מי שנבחר.

<div class="prior-shift-lab" data-lang="he" data-src="/series/classification/artifacts/prior_shift_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/prior-shift-lab.js"></script>

- **בלי תיקון, כמעט כל מודל מרוויח פחות.** ציונים שכוונו לעולם של 6% משאירים את רוב רשומות העתיד מתחת ל-1/8: LightGBM בוחר @@v:temporal_policies.csv|model=LightGBM|correction=none|policy=break-even (1/8)|share_selected|.0%@@ מהרשומות ומרוויח @@v:temporal_policies.csv|model=LightGBM|correction=none|policy=break-even (1/8)|contribution|d@@. Naive Bayes הוא החריג כי ההסתברויות המנופחות שלו בוחרות @@v:temporal_policies.csv|model=Gaussian Naive Bayes|correction=none|policy=break-even (1/8)|share_selected|.0%@@.
- **האורקל מביא את רוב המודלים לבערך "מתקשרים לכולם"**, כי עם השכיחות האמיתית ההסתברויות המתוקנות של כמעט כל רשומה עולות על 1/8: LightGBM בוחר @@v:temporal_policies.csv|model=LightGBM|correction=oracle prevalence (diagnostic)|policy=break-even (1/8)|share_selected|.0%@@ מהרשומות, רגרסיה לוגיסטית @@v:temporal_policies.csv|model=Logistic regression|correction=oracle prevalence (diagnostic)|policy=break-even (1/8)|share_selected|.0%@@. תיקון ש"מחזיר את הרווח" הפך את המדיניות ל"יוצרים קשר עם (כמעט) כולם", והיתרון שלו על "מתקשרים לכולם" הוא כמה יחידות, לא אלפים. המהדורה הראשונה של הסדרה דיווחה 12,240 ל-LightGBM מתוקן מול 12,082 ל"מתקשרים לכולם" (+158). בחישוב מחדש עם פיתוח מהעבר בלבד, LightGBM מתוקן באורקל מרוויח @@v:temporal_policies.csv|model=LightGBM|correction=oracle prevalence (diagnostic)|policy=break-even (1/8)|contribution|d@@.
- **תיקון החלון האחרון הוא דרך ביניים שאפשר לפרוס.** עם שכיחות מאחרת של @@j:temporal_shift.json|prevalence_last_validation_block|.1%@@, היער האקראי, extra trees ו-CatBoost מרוויחים @@v:temporal_policies.csv|model=Random forest|correction=last-window prevalence|policy=break-even (1/8)|contribution|d@@, @@v:temporal_policies.csv|model=Extra trees|correction=last-window prevalence|policy=break-even (1/8)|contribution|d@@ ו-@@v:temporal_policies.csv|model=CatBoost|correction=last-window prevalence|policy=break-even (1/8)|contribution|d@@, בערך 300 עד 430 (2.5% עד 3.5%) מעל "מתקשרים לכולם". Naive Bayes מסיים בטווח של 40 יחידות ממנו ושאר המודלים נשארים מתחתיו. האומדן המאחר עצמו נמוך מדי.
- **EM נכשל כאן.** בשבעה מתוך אחד-עשר מודלים האיטרציה נסחפת לשכיחות קרובה ל-1 ובוחרת כל רשומה. כך נראית הנחה שלא מתקיימת: התפלגויות הקלט בתוך כל מחלקה *לא* נשארו במקום, ולכן האומד סופג את הסחף בקלטים.

@@table:temporal_em_estimates.csv|rename=model:מודל,em_estimate:אומדן שכיחות EM@@

מדיניות פשוטה יותר מדלגת על תיקון ה-prior: בוחרים את הסף שממקסם תרומה על בלוקי האימות בעבר ומפעילים אותו כמות שהוא.

@@table:temporal_policies.csv|where=policy~past-only validation threshold|sort=contribution|desc|cols=model,records_selected,share_selected,contribution,gain_vs_call_everyone|fmt=records_selected:d;share_selected:.0%;contribution:d;gain_vs_call_everyone:+,.0f|rename=model:מודל,records_selected:נבחרו,share_selected:חלק מהרשומות,contribution:תרומה,gain_vs_call_everyone:רווח על "מתקשרים לכולם"@@

רק extra trees מנצח את "מתקשרים לכולם", בכ-@@v:temporal_policies.csv|model=Extra trees|correction=none|policy=past-only validation threshold|gain_vs_call_everyone|+,.0f@@ (5%). עם נקודת איזון של 12.5% ושיעור של 30.8%, "יוצרים קשר כמעט עם כולם" היא כבר מדיניות חזקה ולדירוג נשאר מעט להוסיף.

## למה המובילים השתנו? השערות והסרות

מפתה לומר ש-boosting נכשל כי הוא נשען על עמודות המקרו בעוד רגרסיה לוגיסטית מחלידה בצורה חלקה. הנתונים תומכים בפחות. התאמנו מחדש שלושה מודלים עם ההגדרות שנבחרו תחת שני שינויים, כל אחד משתמש רק בעבר:

@@table:temporal_ablations.csv|cols=model,variant,ap,roc_auc,mean_score,contribution_break_even,selected|fmt=contribution_break_even:d;selected:d|rename=model:מודל,variant:וריאנט,ap:AP,roc_auc:AUC,mean_score:ציון ממוצע,contribution_break_even:תרומה ב-1/8,selected:נבחרו@@

הסרת עמודות המקרו מעלה את ה-AP וה-AUC של רגרסיה לוגיסטית ושל LightGBM אבל מורידה את אלה של היער, והתרומה ב-1/8 זזה בכיוונים שונים (מטה לרגרסיה הלוגיסטית וליער, מעלה ל-LightGBM). אימון על החצי העדכני יותר של העבר מעלה AP ל-LightGBM ולרגרסיה לוגיסטית ומוריד אותו מעט ליער. אף קבוצת עמודות או חלון אימון בודדים לא מסבירים את הסידור מחדש, ולכן התייחסו לסיפור של עמודות המקרו כהשערה שהניסויים האלה לא מאשרים.

אבחון אחד מפריד בין שני סוגי כשל. אחרי תיקון prior של אורקל, שגיאת הכיול של LightGBM יורדת מ-@@j:temporal_shift.json|calibration_effect_of_prior_correction.LightGBM.ece_before|.2f@@ ל-@@j:temporal_shift.json|calibration_effect_of_prior_correction.LightGBM.ece_after_oracle_prior_correction|.2f@@: במודל הזה שיעור הבסיס היה הבעיה העיקרית. ברגרסיה לוגיסטית היא כמעט לא זזה (@@j:temporal_shift.json|calibration_effect_of_prior_correction.Logistic regression.ece_before|.2f@@ ל-@@j:temporal_shift.json|calibration_effect_of_prior_correction.Logistic regression.ece_after_oracle_prior_correction|.2f@@), וזה מצביע על קשר קלט-תוצאה שהשתנה או על הסחף בקלטים.

## מפעילים את המדיניות הזו באמת

שום דבר מזה לא ספציפי למערך הנתונים הזה.

- **בודקים אותה בצורה פרוספקטיבית.** קובעים את המדד לפני המבחן ומשווים את מדיניות המודל לנוהג הנוכחי, ל"מתקשרים לכולם" ולבחירה אקראית באותו גודל על *חלוקה אקראית של השיחות המתוכננות*. שופטים הרשמות תוספתיות נטו מהעלות, לא AP.
- **שומרים מדגם חקירה או ביקורת.** מטפלים בחלק אקראי קטן מהשיחות המתוכננות בלי קשר לציון, ואיפה שמקובל משאירים חלק קטן בלי יצירת קשר. הראשון נותן אומדנים בלתי מוטים של שיעור הבסיס ושל הכיול. השני הוא הדרך היחידה ללמוד מה קורה *בלי* יצירת קשר, ומפריד בין נטייה להגיב לבין uplift (חלק 14).
- **מצפים למשוב מאחר וסלקטיבי.** תוצאות מגיעות באיחור, ולכן חלונות אחרונים לא שלמים. השכיחות בין השיחות שהמודל בחר אינה השכיחות בין כל המועמדים: מודל שבוחר היטב גורם לשיעור הבסיס של עצמו להיראות גבוה.
- **מנטרים ארבעה דברים בנפרד.** דירוג (AP ו-AUC על רשומות עדכניות עם תוויות מול השכיחות), כיול (ציון ממוצע מול שיעור שנצפה, בסך הכול וליד הסף, עם ספירות), מדיניות (רשומות שנבחרו ותרומה מול "מתקשרים לכולם" ובחירה אקראית) וכלכלה (האם רשימת המחירים השתנתה?). מסווג שמבחין בין עבר לעדכני לפי הקלטים הוא אזהרה מוקדמת זולה.
- **מכיילים מחדש או מאמנים מחדש.** אם הדירוג מחזיק אבל הציון הממוצע והשיעור מתפצלים, ושיעור בסיס מעודכן משחזר אמינות ליד הסף (כמו ב-LightGBM כאן), שוקללים מחדש את ה-prior בעזרת מדגם הביקורת או חלון עדכני. אם הדירוג מידרדר מול קו הבסיס, או שעדכון שיעור בסיס לא עוזר (כמו ברגרסיה לוגיסטית כאן), מאמנים מחדש על רשומות עדכניות ומריצים שוב את הפרוטוקול. אימון על החצי העדכני עזר לשניים משלושה מודלים בחלק הזה.
- **שינויים ביכולת טיפול** משנים כמה רשומות יוצרים איתן קשר, לא את הסף. שומרים על המגן: עד היכולת, הציונים הגבוהים קודם, אף פעם לא מתחת לציון נקודת האיזון.
- **מודל פשוט או booster?** מחליטים לפי ראיות שנאספו כמו שתפרסו. בחלק 12 המודלים המועצמים הובילו על חלוקה אקראית; כאן לא, וקו בסיס פשוט ו"מתקשרים לכולם" היו קשים לניצחון. שומרים מודל פשוט בכל השוואה.
- **היקף.** הסדרה הזו עוסקת בסיווג בינארי על טבלה. בעיות רב-מחלקתיות מפיקות וקטור הסתברויות של מחלקות (softmax, או אחד-מול-כולם) וצריכות מדדים לכל מחלקה ובחירה של שיטת ממוצע, כמו בחלק 3. בעיות רב-תוויתיות הן לרוב בעיה בינארית אחת לכל תווית, לכל אחת סף משלה.

## ניתוח ומסקנה: מה למדנו

- **בודקים כמו שפורסים.** המובילים בחלוקה האקראית לא היו המובילים ברשומות מאוחרות, והסדר בתוך בלוק העתיד נשען על מדגם אחד.
- **קוראים בשם למה שהשתנה.** השכיחות עלתה, הקלטים זזו רחוק, והקשר ביניהם לא ידוע. תיקון prior עוסק רק בראשון, וההנחות של EM נכשלו באופן גלוי.
- **משווים ל"מתקשרים לכולם".** תחת המחירים האלה הוא מרוויח @@v:temporal_policies.csv|model=LightGBM|correction=none|policy=break-even (1/8)|call_everyone|d@@; המדיניות הטובות ביותר שאפשר לפרוס מנצחות אותו בכ-2.5% עד 5%.
- **ציונים נכשלים בדרכים שונות.** ב-LightGBM זה היה שיעור הבסיס; ברגרסיה לוגיסטית לא.

## לאן הסדרה מגיעה

1. מסווג תומך ב**החלטה**: קובעים קודם את רגע החיזוי, את הנחות העלות ואת יכולת הטיפול (חלקים 1 ו-14).
2. בודקים זכאות וקודים של הקובץ לפני שמשווים אלגוריתמים (חלק 2).
3. AP, log loss ותרומה מדומה עונים על שאלות שונות מדיוק (חלקים 3, 11, 14).
4. תחת פרוטוקול כתוב אחד, מודלי boosting ו-bagging קיבלו את הציונים הגבוהים ביותר על חלוקה אקראית בהפרש צנוע מעל רגרסיה לוגיסטית, והסדר ביניהם אינו מבוסס (חלקים 12 ו-13).
5. סף צריך לבוא מהכלכלה ולהיבדק, וציונים חייבים להיות מכוילים ליד הסף כדי שאפשר יהיה לקרוא אותם כהסתברויות (חלק 11).
6. מודלים יכולים להסתדר מחדש על רשומות מאוחרות וקו בסיס פשוט יכול להיות קשה לניצחון. בודקים כמו שפורסים.

כל מספר בסדרה הזו נכתב על ידי סקריפט ב-`series/classification/scripts` ונקרא בחזרה על ידי המאמר שמצטט אותו. אם מספר לא משוחזר, זה באג.

*לקריאה נוספת.* Saerens, Latinne ו-Decaestecker (2002), [Adjusting the outputs of a classifier to new a priori probabilities](https://doi.org/10.1162/089976602753284446).

[חזרה לאינדקס הסדרה](/he/series/classification/)
