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

הציון של רשומה הוא 0.125. האם 12.5% מהרשומות עם הציון הזה נרשמות? זה מכריע אם אפשר להפעיל את כלל נקודת האיזון `עלות / ערך` על הפלט של מודל, והמודלים נבדלים מאוד. למודל Gaussian Naive Bayes מחלק 5 יש הסתברות חזויה ממוצעת של @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|mean_score|.2f@@ כשרק @@j:calibration_notes.json|validation_prevalence|.1%@@ מרשומות האימות נרשמות. רגרסיה לוגיסטית סוטה בממוצע ב-@@v:calibration_summary.csv|model=Logistic regression|calibration=none (raw)|ece_10_quantile|.3f@@.

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
(filled in by the build)
```

**מה זה אומר.** הציון הממוצע הגולמי גדול ביותר מפי שניים מהשיעור האמיתי, @@j:calibration_notes.json|validation_prevalence|.3f@@, עם log loss גדול ו-ECE של בערך @@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|ece_10_quantile|.2f@@. אחרי כיול סיגמואידי הציון הממוצע תואם את השיעור, ו-log loss ו-ECE יורדים בחדות, בעוד AP כמעט לא משתנה.

## חמישה מודלים, שלושה טיפולים

ציונים על 6,590 רשומות האימות: בלי תיקון, מכייל סיגמואידי (Platt) ומכייל איזוטוני, כל אחד עטוף סביב התהליך עם הצלבה של 5 קיפולים.

@@table:calibration_summary.csv|where=calibration~none (raw);sigmoid, 5-fold ensemble around the pipeline;isotonic, 5-fold ensemble around the pipeline|cols=model,calibration,average_precision,log_loss,brier,ece_10_quantile,mean_score,distinct_scores|fmt=distinct_scores:d|rename=model:מודל,calibration:כיול,average_precision:AP,log_loss:log loss,brier:Brier,ece_10_quantile:ECE,mean_score:ציון ממוצע,distinct_scores:ציונים שונים@@

![דיאגרמות אמינות על רשומות האימות. שמאל: עשר קבוצות שוות בגודלן; ימין: הגדלה של ציונים עד 0.4, איפה שסף נקודת האיזון 0.125 נמצא. הפסים הם רווחי Wilson של 95%.](/series/classification/figures/ch11-calibration.png)
*איור 1. נקודות על האלכסון מכוילות. Naive Bayes יושב הרבה מתחתיו עד שמתקנים אותו.*

- **רגרסיה לוגיסטית** קרובה למכוילת (ECE @@v:calibration_summary.csv|model=Logistic regression|calibration=none (raw)|ece_10_quantile|.3f@@) ואף מכייל לא משפר אותה. זה ממצא על המודל המותאם הזה, לא ערובה.
- **יער אקראי תלוי בעלים שלו.** בברירת המחדל של הספרייה (עלים של רשומה אחת) ה-log loss הגולמי הוא @@v:calibration_summary.csv|model=Random forest (library default)|calibration=none (raw)|log_loss|.3f@@ וה-ECE @@v:calibration_summary.csv|model=Random forest (library default)|calibration=none (raw)|ece_10_quantile|.3f@@; עם עלים של לפחות 10 ה-ECE הוא @@v:calibration_summary.csv|model=Random forest (min_samples_leaf=10)|calibration=none (raw)|ece_10_quantile|.3f@@. "יערות מכוילים גרוע" מתאר הגדרה, לא יערות.
- **Naive Bayes** צריך תיקון, ושני המכיילים מתקנים log loss ו-ECE. **LightGBM בברירת מחדל** מכויל סביר (ECE @@v:calibration_summary.csv|model=LightGBM (library default)|calibration=none (raw)|ece_10_quantile|.3f@@).
- **מכיילים יכולים לשנות את הדירוג.** העמודות המכוילות הן ממוצע של חמישה מודלים שהותאמו על חלקים שונים משורות האימון, כך שהם מודלים מעט שונים. היער בברירת המחדל משפר AP (@@v:calibration_summary.csv|model=Random forest (library default)|calibration=none (raw)|average_precision|.3f@@ ל-@@v:calibration_summary.csv|model=Random forest (library default)|calibration=sigmoid, 5-fold ensemble around the pipeline|average_precision|.3f@@), וזה נקרא טוב יותר כאפקט של אנסמבל (חלק 7) מאשר כאפקט של כיול.

## תיקו: למה איזוטוני יכול לפגוע בדירוג

מיפוי עולה בהחלט לא יכול לשנות את הדירוג של וקטור ציונים קבוע אחד. מיפוי סיגמואידי עולה בהחלט: AP ו-AUC זהים עד הספרה למטה. מיפוי איזוטוני הוא מדרגות, ולכן הרבה ציונים גולמיים נוחתים על ערך אחד ויוצרים תיקו.

@@table:calibration_rank_checks.csv|cols=model,map,ap_raw,ap_after_map,distinct_scores_raw,distinct_scores_after_map|fmt=distinct_scores_raw:d;distinct_scores_after_map:d|rename=model:מודל,map:מיפוי שהותאם לציוני מחוץ-לקיפול,ap_raw:AP לפני,ap_after_map:AP אחרי,distinct_scores_raw:שונים לפני,distinct_scores_after_map:שונים אחרי@@

איזוטוני משאיר בין 34 ל-76 ציונים שונים ומוריד את ה-AP בכ-0.01 עד 0.02 בכל שורה, כי אי אפשר לסדר תיקו בין רשומות סבירות. אם צריכים גם דירוג וגם הסתברויות, משתמשים במיפוי סיגמואידי אלא אם יש הרבה נתוני כיול, או מדרגים לפי הציון הגולמי ומדווחים את המספר המכויל לידו.

## כיול איפה שזה חשוב

ה-ECE הכללי מחשב ממוצע על כל הטווח, אבל ההחלטה יושבת ב-0.125. כיול לפי חלון ציונים, עם גדלי קבוצות:

@@table:calibration_threshold_windows.csv|cols=model,score_window,records,mean_score,observed_rate,rate_lo,rate_hi|fmt=records:d|rename=model:מודל,score_window:ציון גולמי,records:רשומות,mean_score:ציון ממוצע,observed_rate:שיעור שנצפה,rate_lo:נמוך 95%,rate_hi:גבוה 95%@@

התאמה בין ממוצעי קבוצות היא בדיקה חלשה, לא הוכחה לכיול בתוך חלון. לרגרסיה הלוגיסטית, ל-LightGBM וליער בברירת המחדל יש ציונים ממוצעים בתוך רווח השיעור שנצפה בשלושת החלונות. היער עם עלים של 10 מגזים בחלון 0.15 עד 0.25 (ציון ממוצע @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|mean_score|.3f@@, שיעור שנצפה @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|observed_rate|.3f@@, רווח @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|rate_lo|.3f@@ עד @@v:calibration_threshold_windows.csv|model=Random forest (min_samples_leaf=10)|score_window=[0.15, 0.25)|rate_hi|.3f@@), וגם Naive Bayes (@@v:calibration_threshold_windows.csv|model=Gaussian Naive Bayes|score_window=[0.15, 0.25)|mean_score|.3f@@ מול @@v:calibration_threshold_windows.csv|model=Gaussian Naive Bayes|score_window=[0.15, 0.25)|observed_rate|.3f@@, עם @@v:calibration_threshold_windows.csv|model=Gaussian Naive Bayes|score_window=[0.15, 0.25)|records|d@@ רשומות בלבד). ECE כללי יכול להסתיר בעיה בדיוק במקום שבו מתקבלת ההחלטה.

## מציונים להחלטה

אם יוצרים קשר עם לקוח עם הסתברות אמיתית *p*, התרומה המדומה הצפויה היא `ערך · p − עלות`: עם עלות 1 וערך 8 (להמחשה) היא חיובית כש-`p > עלות / ערך = 0.125`. **סף נקודת האיזון** הזה מניח ארבעה דברים: הציונים מכוילים ליד 0.125, העלות והערך זהים לכל רשומה, יצירת קשר עם רשומה אחת לא משנה את הערך של אחרת, והכמות שממקסמים היא התרומה המדומה הזו (חלק 14 אומר מה היא לא מודדת). כיול Naive Bayes מקטין את הרשומות שנבחרו ב-1/8 מ-@@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|records_at_or_above_break_even|d@@ ל-@@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=sigmoid, 5-fold ensemble around the pipeline|records_at_or_above_break_even|d@@ עם תרומה מדומה גבוהה מעט יותר (@@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=none (raw)|contribution_at_break_even|d@@ ל-@@v:calibration_summary.csv|model=Gaussian Naive Bayes|calibration=sigmoid, 5-fold ensemble around the pipeline|contribution_at_break_even|d@@). הפרשים של כמה עשרות יחידות בין שורות אחרות הם בתוך הרעש של מדגם אימות אחד, ולכן אל תדרגו שיטות כיול לפי תרומה. ולעולם אל תבחרו סף על הרשומות שעליהן אתם מדווחים אותו: בחרו אותו על ציוני פיתוח מחוץ-לקיפול והקפיאו אותו, כמו שחלק 12 עושה.

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
