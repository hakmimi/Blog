---
title: "מה זה בעצם “טוב”? דיוק חיובי, שלמות, ROC ו-PR"
description: "רגרסיה לוגיסטית אחת מדורגת בחמש דרכים: מטריצת בלבול, דוח סיווג, ROC-AUC, דיוק ממוצע ודיוק בראש הרשימה. מה משתנה כשחלקם של החיוביים משתנה והמודל לא."
series: "classification"
lang: "he"
order: 3
date: 2026-09-30
updated: 2026-10-04
keywords: ["דיוק חיובי ושלמות", "roc auc", "דיוק ממוצע", "מטריצת בלבול", "דוח סיווג", "מדדים"]
readingTime: "11 דקות קריאה"
figure: "ch03-threshold-roc-pr.png"
---

בסף של 0.5, רגרסיה לוגיסטית על הנתונים האלה צודקת ב-@@v:metrics_confusion.csv|threshold=0.5|accuracy|.1%@@ מהמקרים ומוצאת @@v:metrics_confusion.csv|threshold=0.5|recall|.0%@@ מהמנויים. בסף של 0.125 היא צודקת ב-@@v:metrics_confusion.csv|threshold=0.125|accuracy|.1%@@ מהמקרים ומוצאת @@v:metrics_confusion.csv|threshold=0.125|recall|.0%@@. אותו מודל, אותם חיזויים. איזו הגדרה "טובה יותר" תלוי במה שמודדים, ולכן החלק הזה עוסק בבחירת המדד.

<div class="callout">

**מטרה.** לדעת על איזה מספר להסתכל כשהמחלקה המעניינת נדירה.

**תוכנית עבודה.** לקבוע מודל אחד, לקרוא את מטריצת הבלבול ואת דוח הסיווג שלו בשני ספים, להפריד בין איכות הדירוג לבין הסף, לבדוק את ROC-AUC ואת הדיוק הממוצע כשחלקם של החיוביים משתנה, ולסיים במדד שמתאים ליכולת טיפול מוגבלת.

</div>

## ציון, סף והחלטה

רוב המסווגים מוציאים **ציון** לכל רשומה, בדרך כלל בין 0 ל-1. **סף** (threshold) הופך אותו להחלטה: בסף או מעליו פירושו "בוחרים". כך נוצרות שתי שאלות. *עד כמה הציון מדרג רשומות היטב?* זו תכונה של המודל. *איפה חותכים?* זו החלטה על עלות ועל יכולת טיפול. הרבה טעויות במדדים נובעות מבלבול בין השתיים.

## מטריצת הבלבול ודוח הסיווג

כל רשומה נוחתת באחד מארבעה תאים (ב-scikit-learn השורות הן האמת, ו-`confusion_matrix(...).ravel()` מחזירה TN, FP, FN, TP). "חיובי" פירושו המחלקה שאנחנו מחפשים, לא "טוב".

| | חזינו לא | חזינו כן |
|---|---|---|
| **בפועל לא** | TN: השארנו בשקט נכון | FP: שיחה מבוזבזת |
| **בפועל כן** | FN: מנוי שהוחמץ | TP: הצלחה |

| מדד | נוסחה | על איזו שאלה הוא עונה |
|---|---|---|
| דיוק (Accuracy) | (TP + TN) / הכול | באיזה אחוז מהמקרים ההחלטה נכונה? |
| דיוק חיובי (Precision) | TP / (TP + FP) | מבין השיחות שבחרנו, כמה מצליחות? |
| שלמות (Recall, שיעור חיוביים אמיתיים) | TP / (TP + FN) | מבין כל המנויים, כמה הגענו אליהם? |
| סגוליות (Specificity) | TN / (TN + FP) | מבין כל מי שלא נרשם, כמה השארנו בשקט? |
| שיעור חיוביים שגויים | FP / (FP + TN) | מבין כל מי שלא נרשם, כמה בחרנו בכל זאת? |
| F1 | 2 · precision · recall / (precision + recall) | גבוה רק כששניהם גבוהים |

`classification_report` מדפיס דיוק חיובי, שלמות ו-F1 לכל מחלקה בנפרד, את גדלי המחלקות (**support**) ושני ממוצעים. **Macro** נותן משקל שווה לכל המחלקות. **Weighted** שוקל אותן לפי ה-support, ולכן בנתונים לא מאוזנים הוא מתאר בעיקר את מחלקת הרוב. אף אחד מהם לא נכון מעצמו: זה תלוי אם אכפת לכם מהמחלקות באותה מידה.

**מימוש.** מתאימים רגרסיה לוגיסטית על שורות הפיתוח (ההגדרה מקופלת למטה), מדרגים את חלק ההשוואה פעם אחת, ומדפיסים את הדוח בשני ספים.

<details>
<summary>קוד ההגדרה</summary>

```python
import numpy as np
import pandas as pd
from sklearn.compose import make_column_transformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])                       # the main feature set (part 2)
dev, cmp_ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
cat = [c for c in X.columns if X[c].dtype == object]
model = make_pipeline(make_column_transformer((OneHotEncoder(handle_unknown="ignore"), cat), remainder=StandardScaler()),
                      LogisticRegression(max_iter=2000))
p = model.fit(X.iloc[dev], y[dev]).predict_proba(X.iloc[cmp_])[:, 1]     # one score per record
yc = y[cmp_]
```

</details>

```python
for t in (0.5, 0.125):
    tn, fp, fn, tp = confusion_matrix(yc, p >= t).ravel()
    print(f"threshold {t}: TN={tn} FP={fp} FN={fn} TP={tp}")
    print(classification_report(yc, p >= t, target_names=["no", "yes"], digits=3))
```

**תוצאה.**

```output
(filled in by the build)
```

**מה זה אומר.** קראו קודם את ה-support (7,310 "לא", 928 "כן"), ואז את השורה של "כן". ב-0.5 המודל מדויק (בערך 0.69) ומוצא מעט (שלמות 0.22). ב-0.125 הוא בוחר הרבה יותר רשומות: הדיוק החיובי יורד ל-0.38 והשלמות עולה ל-0.64. הדיוק (accuracy) ירד מ-0.901 ל-0.842 בזמן שהשלמות וה-F1 של "כן" עלו, כך ש**הדיוק ירד בזמן שהמודל נעשה שימושי יותר למציאת מנויים**. אם זו העסקה הנכונה תלוי בעלות מול ערך (חלק 11). הממוצעים לא מסכימים: macro F1 הוא @@v:metrics_report.csv|threshold=0.5|row=macro avg|f1-score|.3f@@, ו-weighted F1 הוא @@v:metrics_report.csv|threshold=0.5|row=weighted avg|f1-score|.3f@@, כי מחלקת הרוב מושכת את המספר המשוקלל כלפי מעלה.

## איכות הדירוג: ROC ודיוק-שלמות

הזזת הסף משרטטת עקומות. **עקומת ROC** משרטטת שלמות מול שיעור החיוביים השגויים; השטח מתחתיה, **ROC-AUC**, הוא ההסתברות שמנוי אקראי יקבל ציון גבוה ממי שלא נרשם. הוא מתאר הפרדה בין מחלקות, לא כמה מהרשומות שנבחרו נכונות. **עקומת דיוק-שלמות** משרטטת דיוק חיובי מול שלמות. **דיוק ממוצע (AP)** סוכם (עלייה בשלמות) × (דיוק חיובי) על פני ספים, וזה מה ש-`average_precision_score` מחשבת. זה קשור לשטח הטרפזי `auc(recall, precision)` אבל לא זהה לו: כאן @@j:metrics_notes.json|average_precision|.3f@@ ו-@@j:metrics_notes.json|pr_auc_trapezoid|.3f@@. אנחנו משתמשים ב-AP. דירוג אקראי מקבל את חלקם של החיוביים, @@j:metrics_notes.json|prevalence|.3f@@.

![שמאל: דיוק חיובי ושלמות כשהסף זז. מרכז: עקומת ROC. ימין: עקומת דיוק-שלמות עם חלקם של החיוביים כקו הבסיס.](/series/classification/figures/ch03-threshold-roc-pr.png)
*איור 1. שלוש תמונות של ציוני מודל אחד. רק הפאנל השמאלי מראה את הסף.*

## למה ROC-AUC ו-AP לא מסכימים כשהחיוביים נדירים

אותם ציונים נותנים ROC-AUC של @@j:metrics_notes.json|roc_auc|.3f@@ ו-AP של @@j:metrics_notes.json|average_precision|.3f@@. הם עונים על שאלות שונות, ואפשר לראות את זה כששינוי מספר החיוביים משאיר את כל הציונים קבועים.

**מימוש.** מוחקים באקראי חלק מהחיוביים ומחשבים מחדש את שני המדדים (200 מחיקות בכל שורה).

```python
rng = np.random.default_rng(42)
print(f"{'positives kept':>15}{'share positive':>16}{'ROC-AUC':>10}{'AP':>8}{'AP / share':>12}")
for keep in (1.0, 0.5, 0.2, 0.1):
    auc, ap, share = [], [], []
    for _ in range(200 if keep < 1 else 1):
        m = (yc == 0) | (rng.random(len(yc)) < keep)
        auc.append(roc_auc_score(yc[m], p[m])); ap.append(average_precision_score(yc[m], p[m])); share.append(yc[m].mean())
    print(f"{keep:>15.0%}{np.mean(share):>16.3f}{np.mean(auc):>10.3f}{np.mean(ap):>8.3f}{np.mean(ap) / np.mean(share):>12.1f}")
```

**תוצאה.**

```output
(filled in by the build)
```

**מה זה אומר.** ROC-AUC כמעט לא זז: מחיקה אקראית של חיוביים משאירה את התפלגות הציונים של כל מחלקה ללא שינוי. AP יורד בחדות, כי הדיוק החיובי תלוי בתמהיל: עם פחות חיוביים אותו דירוג מכניס יותר מי שלא נרשם בין הרשומות שנבחרו. (AP יחסית לדירוג אקראי דווקא עולה, כך ש-AP תלוי בשכיחות בשני אופנים.) AP לבדו ניתן להשוואה רק בין מודלים על אותן רשומות. ROC-AUC לא "מנופח" בגלל חוסר האיזון; הוא פשוט לא אומר כמה שיחות מבוזבזות מגיעות עם כל הצלחה, וזה מה שהתפעול מרגיש.

## המדד שמתאים ליכולת טיפול

למוקד טלפוני יש יכולת טיפול, לא סף. אם הוא יכול לטפל ב-10% מהרשימה: *מבין 10% העליונים לפי ציון, כמה הם מנויים?*

```python
order = np.argsort(-p)
for share in (0.05, 0.10, 0.20):
    k = int(share * len(p)); hits = yc[order[:k]]
    print(f"top {share:.0%} ({k} records): precision {hits.mean():.2f}, recall {hits.sum() / yc.sum():.2f}, lift {hits.mean() / yc.mean():.1f}x")
```

```output
(filled in by the build)
```

Lift הוא הדיוק החיובי מחולק בשיעור הכללי, ולכן הוא אומר פי כמה ראש הרשימה טוב יותר מאקראי. קל להסביר אותו והוא קשור ליכולת הטיפול, אבל הוא רועש עבור k קטן, ולכן ציינו את מספר הרשומות.

## גוררים את הסף

הווידג'ט משתמש בציוני חלק ההשוואה הקפואים של חמישה מודלים מחלק 12. הזיזו את הסף וצפו במטריצת הבלבול, במיקומים בעקומות ROC ודיוק-שלמות ובתרומה המדומה. המחירים (עלות 1, ערך 8) הם הנחות, והתרומה היא סימולציה רטרוספקטיבית (חלק 14). הסמן הזהוב הוא הסף הטוב ביותר *במדגם הזה*, לא אופטימום של האוכלוסייה.

<div class="threshold-lab" data-lang="he" data-src="/series/classification/artifacts/threshold_lab.json" data-cost="1" data-value="8"></div>
<script src="/js/threshold-lab.js"></script>

## ניתוח ומסקנה: מה למדנו

| אם אכפת לכם מ… | הסתכלו על | היזהרו מ… |
|---|---|---|
| הפרדה בין מחלקות | ROC-AUC | שותק לגבי דיוק חיובי ועומס עבודה |
| שיחות שנבחרו שמצליחות | דיוק ממוצע, דיוק בראש הרשימה | תלוי בשכיחות; משווים על אותן רשומות |
| האיזון בסף אחד | F1 של המחלקה החיובית | מתעלם מ-true negatives; משקל שווה הוא הנחה |
| נכונות כללית | דיוק (accuracy) | נשלט על ידי הרוב; לא לעשות כלום מקבל @@j:metrics_notes.json|always_no_accuracy|.3f@@ |
| יכולת טיפול קבועה | דיוק חיובי ושלמות ב-k הראשונים | רועש עבור k קטן |
| כסף | תרומה בסף (חלק 14) | דורש רשימת מחירים וציונים מכוילים |

לדיוק (accuracy) יש 11 נקודות של מרחב (מ-@@j:metrics_notes.json|always_no_accuracy|.3f@@ עד 1.000), אבל המידע נמצא במחלקת המיעוט. מדד הבחירה הראשי כאן הוא **הדיוק הממוצע**, תמיד ליד חלקם של החיוביים. הסף נקבע בנפרד.

*לקריאה נוספת.* Davis ו-Goadrich (2006), [The relationship between precision-recall and ROC curves](https://doi.org/10.1145/1143844.1143874); Saito ו-Rehmsmeier (2015), [PLOS ONE](https://doi.org/10.1371/journal.pone.0118432); התיעוד של scikit-learn ל-[`average_precision_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html), שמציין במה הוא שונה מהשטח הטרפזי.

[חלק 4](/he/series/classification/04-objective-functions/) מסתכל פנימה אל האימון: מה מודל ממזער, ומה הבחירה משנה?
