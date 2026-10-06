---
title: "האם הציונים הם הסתברויות? כיול, ספים ועלות"
description: "כשמודל אומר 12.5%, האם 12.5% מהרשומות האלה נרשמות? איך בודקים, כמה עולה תיקון מודל בדירוג, ומה סף נקודת האיזון דורש מהציונים."
series: "classification"
lang: "he"
order: 11
date: 2026-09-30
updated: 2026-10-04
keywords: ["כיול", "platt scaling", "רגרסיה איזוטונית", "דיאגרמת אמינות", "שגיאת כיול צפויה", "סף החלטה"]
readingTime: "11 דקות קריאה"
figure: "ch11-calibration.png"
---

הציון של רשומה הוא 0.125. האם 12.5% מהרשומות עם הציון הזה נרשמות? זה מכריע אם אפשר להפעיל את כלל נקודת האיזון `עלות / ערך` על הפלט של מודל, והמודלים נבדלים מאוד. למודל Gaussian Naive Bayes מחלק 5 יש הסתברות חזויה ממוצעת של 0.23 כשרק 11.3% מרשומות האימות נרשמות. רגרסיה לוגיסטית סוטה בממוצע ב-0.005.

<div class="callout">

**מטרה.** לשפוט אם אפשר לקרוא ציונים כהסתברויות ליד סף ההחלטה, ולתקן אותם בלי פגיעה בדירוג מעבר לנחוץ.

**תוכנית עבודה.** למדוד כיול בטבלאות אמינות ובשגיאת הכיול הצפויה. לתקן מודלים בשתי שיטות סטנדרטיות העוטפות את כל התהליך. לבדוק את הדירוג לפני ואחרי. ואז לומר מה סף נקודת האיזון מניח.

</div>

## מה זה "מכויל" ואיך מודדים

ציונים **מכוילים** אם בין רשומות שקיבלו ציון בקרבת *p*, בערך חלק *p* נרשמים. **דיאגרמת אמינות** ממיינת רשומות לפי ציון, חותכת אותן לקבוצות, ומשרטטת את הציון הממוצע מול השיעור שנצפה. **שגיאת הכיול הצפויה (ECE)** היא הפער הממוצע המשוקלל בגודל הקבוצות; היא תלויה באופן שבו חותכים את הקבוצות, ולכן אנחנו משתמשים בעשר קבוצות שוות בגודלן. Log loss וציון Brier מערבבים כיול עם היכולת להפריד בין המחלקות, ולכן אף אחד מהם לא מודד כיול לבדו.

הכול מדורג על שורות שהמודל לא ראה: שורות הפיתוח מחולקות 75/25, מודלים ומכיילים מותאמים על ה-75% (מכיילים עם הצלבה של 5 קיפולים בתוכם), וחלק ההשוואה לא בשימוש. מכייל עוטף את **כל התהליך** (עיבוד מקדים ומודל) כך שכל קיפול מתאים מחדש את שניהם. AP ו-AUC באים מציונים לא חתוכים; חיתוך כדי להימנע מ-log(0) קורה רק בתוך log loss.

**מימוש.** עוטפים את Gaussian Naive Bayes במכייל.

<details>
<summary>קוד ההגדרה</summary>

```python
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import make_column_transformer
from sklearn.metrics import average_precision_score, log_loss
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

df = pd.read_csv("bank-additional-full.csv", sep=";")
y = (df.pop("y") == "yes").astype(int).to_numpy()
X = df.drop(columns=["duration", "campaign"])
dev, _ = train_test_split(np.arange(len(X)), test_size=0.2, stratify=y, random_state=42)
dev = np.sort(dev)
fit, val = train_test_split(dev, test_size=0.25, stratify=y[dev], random_state=42)
cat = [c for c in X.columns if X[c].dtype == object]

def pipeline():
    prep = make_column_transformer((OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat), remainder=StandardScaler())
    return make_pipeline(prep, GaussianNB())

def ece(y_true, p, bins=10):                       # expected calibration error with equal-count bins
    edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    which = np.clip(np.digitize(p, edges[1:-1]), 0, len(edges) - 2)
    return sum((which == b).mean() * abs(p[which == b].mean() - y_true[which == b].mean()) for b in np.unique(which))
```

</details>

```python
raw = pipeline().fit(X.iloc[fit], y[fit]).predict_proba(X.iloc[val])[:, 1]
cv = StratifiedKFold(5, shuffle=True, random_state=42)
cal = CalibratedClassifierCV(pipeline(), method="sigmoid", cv=cv).fit(X.iloc[fit], y[fit]).predict_proba(X.iloc[val])[:, 1]
yv = y[val]
for name, p in (("raw", raw), ("sigmoid, calibrated", cal)):
    print(f"{name:<20} mean score {p.mean():.3f}  log loss {log_loss(yv, np.clip(p, 1e-12, 1 - 1e-12)):.3f}  "
          f"ECE {ece(yv, p):.3f}  AP {average_precision_score(yv, p):.3f}")
```

**תוצאה.**

```output
raw                  mean score 0.230  log loss 2.311  ECE 0.189  AP 0.352
sigmoid, calibrated  mean score 0.114  log loss 0.307  ECE 0.039  AP 0.355
```

**מה זה אומר.** הציון הממוצע הגולמי גדול ביותר מפי שניים מהשיעור האמיתי, 0.113, עם log loss גדול ו-ECE של בערך 0.19. אחרי כיול סיגמואידי הציון הממוצע תואם את השיעור, ו-log loss ו-ECE יורדים בחדות, בעוד AP כמעט לא משתנה.

## חמישה מודלים, שלושה טיפולים

ציונים על 6,590 רשומות האימות: בלי תיקון, מכייל סיגמואידי (Platt) ומכייל איזוטוני, כל אחד עטוף סביב התהליך עם הצלבה של 5 קיפולים.

| מודל | כיול | AP | log loss | Brier | ECE | ציון ממוצע | ציונים שונים |
|---|---|---|---|---|---|---|---|
| Logistic regression | none (raw) | 0.461 | 0.277 | 0.078 | 0.005 | 0.114 | 8,024 |
| Logistic regression | sigmoid, 5-fold ensemble around the pipeline | 0.461 | 0.277 | 0.078 | 0.005 | 0.113 | 8,024 |
| Logistic regression | isotonic, 5-fold ensemble around the pipeline | 0.457 | 0.287 | 0.078 | 0.007 | 0.114 | 1,093 |
| Random forest (library default) | none (raw) | 0.394 | 0.376 | 0.087 | 0.038 | 0.117 | 1,769 |
| Random forest (library default) | sigmoid, 5-fold ensemble around the pipeline | 0.413 | 0.290 | 0.083 | 0.013 | 0.113 | 7,635 |
| Random forest (library default) | isotonic, 5-fold ensemble around the pipeline | 0.415 | 0.288 | 0.082 | 0.005 | 0.113 | 3,024 |
| Random forest (min_samples_leaf=10) | none (raw) | 0.467 | 0.274 | 0.077 | 0.010 | 0.114 | 8,023 |
| Random forest (min_samples_leaf=10) | sigmoid, 5-fold ensemble around the pipeline | 0.466 | 0.274 | 0.077 | 0.011 | 0.114 | 8,024 |
| Random forest (min_samples_leaf=10) | isotonic, 5-fold ensemble around the pipeline | 0.464 | 0.274 | 0.077 | 0.008 | 0.114 | 2,086 |
| Gaussian Naive Bayes | none (raw) | 0.352 | 2.311 | 0.189 | 0.189 | 0.230 | 7,385 |
| Gaussian Naive Bayes | sigmoid, 5-fold ensemble around the pipeline | 0.355 | 0.307 | 0.089 | 0.039 | 0.114 | 7,398 |
| Gaussian Naive Bayes | isotonic, 5-fold ensemble around the pipeline | 0.351 | 0.294 | 0.084 | 0.007 | 0.114 | 445 |
| LightGBM (library default) | none (raw) | 0.459 | 0.275 | 0.078 | 0.009 | 0.115 | 2,912 |
| LightGBM (library default) | sigmoid, 5-fold ensemble around the pipeline | 0.468 | 0.275 | 0.077 | 0.016 | 0.114 | 7,822 |
| LightGBM (library default) | isotonic, 5-fold ensemble around the pipeline | 0.468 | 0.272 | 0.077 | 0.007 | 0.114 | 3,117 |

![דיאגרמות אמינות על רשומות האימות. שמאל: עשר קבוצות שוות בגודלן; ימין: הגדלה של ציונים עד 0.4, איפה שסף נקודת האיזון 0.125 נמצא. הפסים הם רווחי Wilson של 95%.](/series/classification/figures/ch11-calibration.png)
*איור 1. נקודות על האלכסון מכוילות. Naive Bayes יושב הרבה מתחתיו עד שמתקנים אותו.*

- **רגרסיה לוגיסטית** קרובה למכוילת (ECE 0.005) ואף מכייל לא משפר אותה. זה ממצא על המודל המותאם הזה, לא ערובה.
- **יער אקראי תלוי בעלים שלו.** בברירת המחדל של הספרייה (עלים של רשומה אחת) ה-log loss הגולמי הוא 0.376 וה-ECE 0.038; עם עלים של לפחות 10 ה-ECE הוא 0.010. "יערות מכוילים גרוע" מתאר הגדרה, לא יערות.
- **Naive Bayes** צריך תיקון, ושני המכיילים מתקנים log loss ו-ECE. **LightGBM בברירת מחדל** מכויל סביר (ECE 0.009).
- **מכיילים יכולים לשנות את הדירוג.** העמודות המכוילות הן ממוצע של חמישה מודלים שהותאמו על חלקים שונים משורות האימון, כך שהם מודלים מעט שונים. היער בברירת המחדל משפר AP (0.394 ל-0.413), וזה נקרא טוב יותר כאפקט של אנסמבל (חלק 7) מאשר כאפקט של כיול.

## תיקו: למה איזוטוני יכול לפגוע בדירוג

מיפוי עולה בהחלט לא יכול לשנות את הדירוג של וקטור ציונים קבוע אחד. מיפוי סיגמואידי עולה בהחלט: AP ו-AUC זהים עד הספרה למטה. מיפוי איזוטוני הוא מדרגות, ולכן הרבה ציונים גולמיים נוחתים על ערך אחד ויוצרים תיקו.

| מודל | מיפוי שהותאם לציוני מחוץ-לקיפול | AP לפני | AP אחרי | שונים לפני | שונים אחרי |
|---|---|---|---|---|---|
| Logistic regression | sigmoid | 0.461 | 0.461 | 8,024 | 8,024 |
| Logistic regression | isotonic | 0.461 | 0.442 | 8,024 | 68 |
| Random forest (library default) | sigmoid | 0.394 | 0.394 | 1,769 | 1,691 |
| Random forest (library default) | isotonic | 0.394 | 0.378 | 1,769 | 47 |
| Random forest (min_samples_leaf=10) | sigmoid | 0.467 | 0.467 | 8,023 | 8,023 |
| Random forest (min_samples_leaf=10) | isotonic | 0.467 | 0.451 | 8,023 | 76 |
| Gaussian Naive Bayes | sigmoid | 0.352 | 0.352 | 7,385 | 7,385 |
| Gaussian Naive Bayes | isotonic | 0.352 | 0.343 | 7,385 | 34 |
| LightGBM (library default) | sigmoid | 0.459 | 0.459 | 2,912 | 2,912 |
| LightGBM (library default) | isotonic | 0.459 | 0.442 | 2,912 | 47 |

איזוטוני משאיר בין 34 ל-76 ציונים שונים ומוריד את ה-AP בכ-0.01 עד 0.02 בכל שורה, כי אי אפשר לסדר תיקו בין רשומות סבירות. אם צריכים גם דירוג וגם הסתברויות, משתמשים במיפוי סיגמואידי אלא אם יש הרבה נתוני כיול, או מדרגים לפי הציון הגולמי ומדווחים את המספר המכויל לידו.

## כיול איפה שזה חשוב

ה-ECE הכללי מחשב ממוצע על כל הטווח, אבל ההחלטה יושבת ב-0.125. כיול לפי חלון ציונים, עם גדלי קבוצות:

| מודל | ציון גולמי | רשומות | ציון ממוצע | שיעור שנצפה | נמוך 95% | גבוה 95% |
|---|---|---|---|---|---|---|
| Logistic regression | [0.05, 0.10) | 3,010 | 0.067 | 0.063 | 0.055 | 0.073 |
| Logistic regression | [0.10, 0.15) | 483 | 0.118 | 0.108 | 0.083 | 0.138 |
| Logistic regression | [0.15, 0.25) | 442 | 0.201 | 0.197 | 0.162 | 0.236 |
| Random forest (library default) | [0.05, 0.10) | 1,196 | 0.070 | 0.066 | 0.053 | 0.082 |
| Random forest (library default) | [0.10, 0.15) | 565 | 0.122 | 0.103 | 0.080 | 0.130 |
| Random forest (library default) | [0.15, 0.25) | 562 | 0.192 | 0.183 | 0.153 | 0.217 |
| Random forest (min_samples_leaf=10) | [0.05, 0.10) | 2,952 | 0.069 | 0.063 | 0.054 | 0.072 |
| Random forest (min_samples_leaf=10) | [0.10, 0.15) | 489 | 0.119 | 0.112 | 0.087 | 0.144 |
| Random forest (min_samples_leaf=10) | [0.15, 0.25) | 213 | 0.193 | 0.127 | 0.089 | 0.178 |
| Gaussian Naive Bayes | [0.05, 0.10) | 158 | 0.073 | 0.101 | 0.063 | 0.158 |
| Gaussian Naive Bayes | [0.10, 0.15) | 118 | 0.125 | 0.127 | 0.079 | 0.199 |
| Gaussian Naive Bayes | [0.15, 0.25) | 117 | 0.195 | 0.094 | 0.053 | 0.161 |
| LightGBM (library default) | [0.05, 0.10) | 4,169 | 0.066 | 0.064 | 0.057 | 0.072 |
| LightGBM (library default) | [0.10, 0.15) | 434 | 0.119 | 0.090 | 0.066 | 0.120 |
| LightGBM (library default) | [0.15, 0.25) | 231 | 0.198 | 0.208 | 0.160 | 0.265 |

התאמה בין ממוצעי קבוצות היא בדיקה חלשה, לא הוכחה לכיול בתוך חלון. לרגרסיה הלוגיסטית, ל-LightGBM וליער בברירת המחדל יש ציונים ממוצעים בתוך רווח השיעור שנצפה בשלושת החלונות. היער עם עלים של 10 מגזים בחלון 0.15 עד 0.25 (ציון ממוצע 0.193, שיעור שנצפה 0.127, רווח 0.089 עד 0.178), וגם Naive Bayes (0.195 מול 0.094, עם 117 רשומות בלבד). ECE כללי יכול להסתיר בעיה בדיוק במקום שבו מתקבלת ההחלטה.

## מציונים להחלטה

אם יוצרים קשר עם לקוח עם הסתברות אמיתית *p*, התרומה המדומה הצפויה היא `ערך · p − עלות`: עם עלות 1 וערך 8 (להמחשה) היא חיובית כש-`p > עלות / ערך = 0.125`. **סף נקודת האיזון** הזה מניח ארבעה דברים: הציונים מכוילים ליד 0.125, העלות והערך זהים לכל רשומה, יצירת קשר עם רשומה אחת לא משנה את הערך של אחרת, והכמות שממקסמים היא התרומה המדומה הזו (חלק 14 אומר מה היא לא מודדת). כיול Naive Bayes מקטין את הרשומות שנבחרו ב-1/8 מ-2,207 ל-1,947 עם תרומה מדומה גבוהה מעט יותר (2,585 ל-2,605). הפרשים של כמה עשרות יחידות בין שורות אחרות הם בתוך הרעש של מדגם אימות אחד, ולכן אל תדרגו שיטות כיול לפי תרומה. ולעולם אל תבחרו סף על הרשומות שעליהן אתם מדווחים אותו: בחרו אותו על ציוני פיתוח מחוץ-לקיפול והקפיאו אותו, כמו שחלק 12 עושה.

סף אינו כלל ההחלטה היחיד.

| מדיניות | כלל | מתאים כש… |
|---|---|---|
| סף נקודת איזון | בוחרים אם p ≥ עלות / ערך | יכולת הטיפול לא מגבילה והציונים מכוילים ליד הסף |
| Top-k לפי ציון | בוחרים את k הציונים הגבוהים ביותר | יכולת הטיפול קבועה ורק הדירוג מהימן |
| נקודת איזון עם תקרה | בוחרים לכל היותר k, הגבוהים קודם, אף פעם לא מתחת לנקודת האיזון | יכולת הטיפול היא תקרה, לא חובה |
| ספים לפי קטעים | חיתוכים שונים לכל קבוצה | עלויות או ערכים שונים לפי ערוץ או קטע |

## ניתוח ומסקנה: מה למדנו

- **בודקים לפני שמתקנים.** רגרסיה לוגיסטית והיער עם עלים של 10 היו קרובים למכוילים בסך הכול; Naive Bayes לא. כיול תלוי במודל *ובהגדרות שלו*, ו-ECE כללי יכול להסתיר חלון שחשוב.
- **העדיפו מיפוי סיגמואידי** אלא אם נתוני הכיול בשפע: הוא שומר את הדירוג בדיוק, בעוד מיפויים איזוטוניים יצרו תיקו והורידו AP בכל שורה.
- **עוטפים את המכייל סביב כל התהליך** ומחשבים AP ו-AUC מציונים לא חתוכים.
- **סף נקודת האיזון הוא הצהרה על הסתברויות מכוילות ליד ערך אחד.** בודקים קודם את האזור הזה, עם ספירות ורווחים.

*לקריאה נוספת.* Platt (1999), Probabilistic outputs for support vector machines; Zadrozny ו-Elkan (2002), [Transforming classifier scores into accurate multiclass probability estimates](https://doi.org/10.1145/775047.775151); Niculescu-Mizil ו-Caruana (2005), [Predicting good probabilities with supervised learning](https://doi.org/10.1145/1102351.1102430).

[חלק 12](/he/series/classification/12-head-to-head-leaderboard/) מריץ את כל שנים-עשר המודלים תחת פרוטוקול אחד ומתמחר את התוצאה.
