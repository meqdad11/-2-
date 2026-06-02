import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import ContextTypes
import database as db
from helpers import is_admin

logger = logging.getLogger(__name__)
temp_points = {}
temp_games = {}

# ========== قائمة الاقتباسات اليومية (400 اقتباس) ==========
DAILY_QUOTES = [
    "كل يوم جديد فرصة لبداية جديدة. 🌅",
    "خذ الأمور خطوة بخطوة. 🌱",
    "من حقك أن ترتاح عندما تحتاج لذلك. 🌿",
    "التقدم البسيط ما زال تقدماً. 👣",
    "طلب المساعدة دليل وعي وشجاعة. 🤝",
    "ليس عليك أن تحمل كل شيء وحدك. 🤍",
    "العواصف لا تدوم إلى الأبد. ☀️",
    "امنح نفسك بعض اللطف اليوم. 🌸",
    "الراحة جزء مهم من التعافي. 🌷",
    "حتى أصغر إنجاز يستحق التقدير. ⭐",
    "الأيام الصعبة تمر مهما طالت. 🌤️",
    "ركز على ما تستطيع فعله اليوم. 🍃",
    "لا بأس إن لم يكن يومك مثالياً. 🌱",
    "كل خطوة للأمام لها قيمتها. 🚶",
    "امنح نفسك الوقت الذي تحتاجه. ⏳",
    "وجودك مهم وله قيمة. 🤍",
    "من الطبيعي أن تحتاج إلى الدعم أحياناً. 🌿",
    "الأمل قد يبدأ بفكرة صغيرة. ✨",
    "التعافي رحلة وليس سباقاً. 🛤️",
    "اهتم بنفسك كما تهتم بمن تحب. 🌸",
    "يمكنك البدء من جديد في أي وقت. 🌅",
    "ليس مطلوباً منك أن تكون قوياً دائماً. 🍀",
    "كل يوم فرصة جديدة للتعلم والنمو. 🌱",
    "بعض الراحة اليوم قد تصنع فرقاً غداً. 🌼",
    "صوتك ومشاعرك يستحقان الاحترام. 👂",
    "الأمور العظيمة تبدأ بخطوات صغيرة. 🌟",
    "خذ وقتك، لا حاجة للاستعجال. ⏳",
    "الصبر يساعد على تجاوز الكثير. 🌿",
    "قد يكون اليوم أفضل مما تتوقع. ☀️",
    "أنت تستحق معاملة نفسك بلطف. 🌸",
    "الهدوء أحياناً إنجاز بحد ذاته. 🕊️",
    "التغيير يحتاج إلى وقت، وهذا طبيعي. 🌱",
    "كل محاولة للعناية بنفسك مهمة. 🌷",
    "الغد يحمل فرصاً جديدة. 🌄",
    "التعثر لا يلغي التقدم الذي حققته. 🌿",
    "خطوة واحدة تكفي لهذا اليوم. 👣",
    "لا بأس أن تطلب المساندة. 🤝",
    "يمكن للأمل أن ينمو حتى في الأيام الصعبة. 🌱",
    "اعتنِ بنفسك دون شعور بالذنب. 🤍",
    "كل يوم يمنحك فرصة أخرى للمحاولة. 🌅",
    "التقدم لا يُقاس بالسرعة فقط. 🛤️",
    "امنح نفسك فرصة للهدوء. 🍃",
    "لا تحكم على نفسك بقسوة. 🌸",
    "يوماً بعد يوم تتغير الأمور. 🌤️",
    "وجود من يستمع يحدث فرقاً. 💙",
    "يكفي أنك ما زلت تحاول. ⭐",
    "لا بأس أن تأخذ استراحة قصيرة. 🌼",
    "كن صبوراً مع نفسك. 🌿",
    "كل صباح بداية جديدة. ☀️",
    "الأمل لا يحتاج إلى ظروف مثالية لينمو. ✨",
    "الأيام المختلفة جزء طبيعي من الحياة. 🍂",
    "خذ ما تحتاجه من وقت للتعافي. 🌱",
    "التقدم الهادئ ما زال تقدماً حقيقياً. 🚶",
    "أحياناً تكون الراحة أفضل قرار. 🌷",
    "مشوار الألف ميل يبدأ بخطوة. 👣",
    "الحياة تتغير باستمرار، وكذلك الصعوبات. 🌤️",
    "الاعتناء بنفسك أمر مهم. 🌸",
    "هناك دائماً فرصة لبداية جديدة. 🌅",
    "الأوقات الصعبة لا تدوم للأبد. ☀️",
    "يوجد دائماً ما يستحق التمسك بالأمل من أجله. 🤍",
    "امنح نفسك فرصة جديدة كل يوم. 🌱",
    "الرحلة الطويلة تبدأ بخطوة صغيرة. 👣",
    "لا بأس أن تسير ببطء ما دمت تتقدم. 🌿",
    "التنفس بعمق قد يساعد على تهدئة اللحظة. 🍃",
    "كل يوم تعيشه هو خبرة جديدة. 📖",
    "المرونة تساعد على تجاوز التحديات. 🌊",
    "يمكنك المحاولة مرة أخرى متى شئت. 🌅",
    "لا تقارن طريقك بطريق الآخرين. 🛤️",
    "استمع إلى احتياجاتك باهتمام. 🤍",
    "بعض الإنجازات لا يراها إلا صاحبها. ⭐",
    "أعطِ نفسك التقدير الذي تستحقه. 🌸",
    "لا بأس أن تتوقف قليلاً لتلتقط أنفاسك. 🌿",
    "كل يوم يحمل احتمالاً جديداً. ✨",
    "تذكر أن العناية بالنفس ليست رفاهية. 🌷",
    "الصعوبات لا تلغي نقاط قوتك. 🛡️",
    "ما زال أمامك الكثير من الفرص. 🌄",
    "حاول التركيز على خطوة اليوم فقط. 👣",
    "الأمل ينمو مع الاستمرار. 🌱",
    "لك الحق في الشعور بما تشعر به. 💙",
    "التقدم الصغير أفضل من الوقوف في المكان. 🚶",
    "كل محاولة جديدة تستحق الاحترام. 🌟",
    "امنح نفسك بعض الهدوء وسط الانشغال. 🕊️",
    "لا تحتاج إلى الكمال لتكون جيداً. 🌿",
    "قد يكون الغد مختلفاً عما تتوقع. ☀️",
    "الصبر مع النفس مهارة مهمة. 🌱",
    "كل لحظة بداية محتملة. 🌅",
    "خذ استراحة إذا شعرت بالحاجة إليها. 🌼",
    "الأيام الصعبة لا تعرّف شخصيتك بالكامل. 🍂",
    "التغيير يحدث أحياناً بشكل تدريجي. 🌿",
    "من الطبيعي أن تختلف طاقتك من يوم لآخر. 🌱",
    "يكفي أن تبذل ما تستطيع اليوم. 🤍",
    "التقدم لا يحتاج إلى خطوات كبيرة دائماً. 👣",
    "لا بأس أن تطلب وقتاً لنفسك. 🌸",
    "كل شروق شمس يحمل فرصة جديدة. 🌄",
    "ما دمت تحاول فأنت تتحرك للأمام. ⭐",
    "الأمل قد يظهر في أبسط التفاصيل. ✨",
    "اليوم الجديد لا يطلب منك أكثر من خطوة واحدة. 🌱",
    "لا بأس أن يكون تقدمك هادئاً وغير ملحوظ للآخرين. 🌿",
    "كل يوم تمنح فيه نفسك فرصة هو يوم مهم. 🌅",
    "بعض الراحة الآن قد تساعدك لاحقاً. 🌸",
    "الطريق الطويل يُقطع خطوة خطوة. 👣",
    "تذكر أن تأخذ وقتاً لنفسك اليوم. 🤍",
    "لا تحتاج إلى إنجاز كل شيء دفعة واحدة. 🌱",
    "الاستمرار البسيط يصنع فرقاً مع الوقت. ⭐",
    "كل صباح يحمل إمكانية لبداية جديدة. ☀️",
    "امنح نفسك مساحة للتعلم والنمو. 🌿",
    "لا بأس إن احتجت إلى التمهل قليلاً. 🍃",
    "كل محاولة جديدة تستحق التقدير. 🌷",
    "قد لا ترى التغيير فوراً، لكنه قد يكون يحدث. ✨",
    "التعافي لا يسير دائماً بخط مستقيم. 🛤️",
    "يكفي أن تفعل ما تستطيع اليوم. 🤍",
    "الخطوات الصغيرة تتراكم لتصبح إنجازات كبيرة. 🌟",
    "لا تقلل من قيمة المحاولة. 🌱",
    "من الطبيعي أن تكون بعض الأيام أثقل من غيرها. 🌤️",
    "يمكنك البدء من حيث أنت الآن. 🚶",
    "الهدوء يمنح العقل فرصة للترتيب. 🕊️",
    "أحياناً يكون التوقف المؤقت جزءاً من التقدم. 🌿",
    "كل يوم فرصة جديدة للاهتمام بنفسك. 🌸",
    "لا تحمل نفسك فوق طاقتها. 🍃",
    "الأمل لا يشترط أن يكون كبيراً ليكون مفيداً. ✨",
    "الاعتناء بالنفس استثمار طويل الأمد. 🌱",
    "الصبر يساعد على تجاوز المراحل الصعبة. 🌷",
    "تذكر أن الإنجاز ليس المقياس الوحيد لقيمة اليوم. 🤍",
    "لا بأس أن تطلب الدعم عندما تحتاجه. 🤝",
    "كل خطوة واعية نحو الأفضل تستحق الفخر. ⭐",
    "امنح نفسك فرصة جديدة كلما احتجت إليها. 🌅",
    "قد تكون أقرب لهدفك مما تتصور. 🌄",
    "التقدم البطيء ما زال تقدماً. 👣",
    "ليس مطلوباً منك معرفة كل الإجابات الآن. 🌿",
    "خذ الأمور كما تأتي، يوماً بيوم. 🍃",
    "كل لحظة هدوء لها قيمتها. 🕊️",
    "من حقك أن تمنح نفسك وقتاً للراحة. 🌸",
    "التجارب الصعبة لا تدوم إلى الأبد. 🌤️",
    "استمر في الاعتناء بنفسك مهما كانت الخطوات صغيرة. 🌱",
    "لا بأس أن تضع نفسك ضمن أولوياتك. 🤍",
    "كل بداية صغيرة تستحق الاحترام. 🌟",
    "قد يحمل الغد ما لم تتوقعه اليوم. ✨",
    "أعطِ نفسك الإذن بأن تتقدم على طريقتك. 🌿",
    "الأيام المتعبة جزء من الحياة وليست كلها. 🌷",
    "كل محاولة للتغيير لها قيمة. 🌱",
    "التنفس بعمق أحياناً يساعد على ترتيب الأفكار. 🍃",
    "تذكر أن تعاملك مع نفسك مهم أيضاً. 🤍",
    "لا يوجد وقت متأخر للبدء من جديد. 🌅",
    "خطوة صغيرة اليوم خير من انتظار الوقت المثالي. 👣",
    "يمكنك أن تكون فخوراً بمحاولاتك. ⭐",
    "بعض الأمور تحتاج إلى وقت أكثر مما نتوقع. 🌿",
    "لا بأس أن يكون يومك عادياً. ☀️",
    "كل يوم يحمل فرصة للتعلم ولو بشيء بسيط. 📖",
    "امنح نفسك قدراً من المرونة. 🌱",
    "الراحة ليست كسلاً عندما تكون بحاجة إليها. 🌸",
    "قدرتك على الاستمرار تستحق التقدير. 🤍",
    "الأمل قد ينمو تدريجياً مع الأيام. ✨",
    "لا تقارن تقدمك بمعايير الآخرين. 🛤️",
    "الخطوات الصغيرة المتكررة تصنع الفرق. 🚶",
    "كل يوم فرصة جديدة للعناية بنفسك. 🌷",
    "يمكن للهدوء أن يكون قوة أيضاً. 🕊️",
    "من الطبيعي أن تتغير المشاعر من يوم لآخر. 🌿",
    "لا بأس أن تطلب وقتاً إضافياً لنفسك. 🌱",
    "كل جهد تبذله له قيمة حتى لو لم ترَ نتيجته فوراً. ⭐",
    "اسمح لنفسك بأن تتعلم من التجارب. 📚",
    "الغد صفحة جديدة لم تُكتب بعد. 🌄",
    "بعض الخطوات المهمة تكون غير مرئية للآخرين. 🤍",
    "الاستمرار أهم من الكمال. 🌱",
    "كل مرة تنهض فيها هي نجاح بحد ذاته. 🌟",
    "امنح نفسك فرصة للبدء مجدداً. 🌅",
    "لا بأس أن تشعر بالتعب أحياناً. 🌿",
    "الأيام الهادئة تستحق التقدير أيضاً. 🍃",
    "كل تقدم يستحق الاحتفال مهما كان صغيراً. 🎉",
    "خذ وقتك، فالطريق ليس سباقاً. 🛤️",
    "يمكنك أن تتقدم بطريقتك الخاصة. 🌸",
    "بعض الإنجازات تبدأ بقرار بسيط. ✨",
    "من حقك أن تبحث عما يمنحك الراحة. 🤍",
    "كل صباح فرصة جديدة للمحاولة. ☀️",
    "لا تحمل همّ الغد كله دفعة واحدة. 🌱",
    "الخطوات الثابتة تقود إلى أماكن بعيدة. 👣",
    "قد يكون اليوم بداية شيء جيد. 🌄",
    "الاهتمام بالنفس عادة تستحق الاستمرار. 🌷",
    "كل لحظة وعي بنفسك لها قيمة. 🌿",
    "يمكنك التوقف قليلاً ثم المتابعة. 🚶",
    "لا بأس أن تكون رحلتك مختلفة. 🛤️",
    "التغيير الصغير اليوم قد يصنع فرقاً غداً. ✨",
    "تذكر أن تمنح نفسك بعض التقدير. 🤍",
    "الأيام تمر، وكذلك الصعوبات. 🌤️",
    "كل فرصة جديدة تستحق أن تُمنح لنفسك. 🌅",
    "يكفي أنك ما زلت تحاول وتتقدم. ⭐",
    "الطمأنينة قد تبدأ بخطوة بسيطة. 🌸",
    "أنت تستحق يوماً هادئاً ولطيفاً. 🌿",
    "لا بأس أن تبدأ من جديد متى احتجت. 🌱",
    "هناك دائماً مساحة لأمل جديد. ✨",
    "كل يوم تمنح فيه نفسك فرصة جديدة هو مكسب. 🌅",
    "لا بأس أن يكون تقدمك بطيئاً ما دام مستمراً. 🌱",
    "يمكنك أن تبدأ من جديد في أي لحظة. ✨",
    "الراحة جزء طبيعي من أي رحلة طويلة. 🌿",
    "أعطِ نفسك ما تعطيه للآخرين من لطف. 🌸",
    "التعثر لا يعني التوقف عن التقدم. 🚶",
    "لا بأس أن تأخذ وقتك في ترتيب أمورك. 🍃",
    "من الطبيعي أن تحتاج إلى المساندة أحياناً. 🤝",
    "بعض الأيام تحتاج إلى صبر أكثر من غيرها. 🌱",
    "الأمل ينمو خطوة بخطوة. ✨",
    "يكفي أن تبذل أفضل ما تستطيع اليوم. 🤍",
    "لا تحكم على نفسك من خلال يوم واحد فقط. 🌿",
    "قد تكون أقوى مما تظن في مواجهة الصعوبات. ⭐",
    "الهدوء يمنحك مساحة للتفكير بوضوح. 🕊️",
    "الأمور الكبيرة تبدأ بخطوات بسيطة. 👣",
    "لا بأس أن تتوقف قليلاً لتستعيد طاقتك. 🌱",
    "كل تقدم يستحق أن تلاحظه. 🌟",
    "بعض التغييرات تحتاج إلى وقت حتى تظهر. 🍃",
    "من حقك أن تضع راحتك ضمن أولوياتك. 🤍",
    "الأيام المتعبة لا تلغي الأيام الجيدة القادمة. 🌄",
    "استمر في المحاولة مهما كانت الخطوات صغيرة. 🌿",
    "كل بداية جديدة تحمل احتمالاً جديداً. ✨",
    "لا يوجد طريق واحد صحيح للجميع. 🛤️",
    "التقدم الحقيقي لا يحتاج إلى سرعة. 🚶",
    "كل يوم فرصة لتخفيف حمل صغير عن نفسك. 🌷",
    "الصبر على النفس مهارة تستحق التعلم. 🌱",
    "يمكنك أن تكون فخوراً باستمرارك. ⭐",
    "لا بأس أن تحتاج إلى وقت إضافي. 🌸",
    "أحياناً يكون الهدوء أفضل إنجاز في اليوم. 🕊️",
    "الأمل قد يأتي من أبسط التفاصيل. ✨",
    "لا تقارن رحلتك برحلات الآخرين. 🌿",
    "كل صباح بداية صفحة جديدة. 🌅",
    "التعافي يحتاج إلى مساحة وصبر. 🌱",
    "يكفي أنك لم تتوقف عن المحاولة. 🤍",
    "كل يوم يحمل فرصة مختلفة. 🌄",
    "الاعتناء بالنفس ليس أمراً ثانوياً. 🌷",
    "قد يكون الغد أخف مما تتوقع. ☀️",
    "التقدم الصغير أفضل من الجمود. 🚶",
    "كل جهد صادق له قيمة. ⭐",
    "أعطِ نفسك فرصة للنمو بهدوء. 🌱",
    "بعض الإنجازات تبدأ بقرار بسيط. ✨",
    "لا تحمل نفسك أكثر مما تستطيع. 🌿",
    "كل يوم جديد يحمل احتمالاً للتغيير. 🌅",
    "الراحة لا تقل أهمية عن الجهد. 🌸",
    "استمر بخطوتك الحالية، فهذا يكفي الآن. 👣",
    "الأيام تتبدل، وكذلك الظروف. 🌤️",
    "يمكنك أن تمنح نفسك بداية جديدة متى شئت. 🌄",
    "كل مرة تحاول فيها هي خطوة للأمام. 🌱",
    "لا بأس أن تبحث عما يمنحك الطمأنينة. 🕊️",
    "الأمل لا يحتاج إلى الكمال لينمو. ✨",
    "كل يوم فرصة لتكون ألطف مع نفسك. 🤍",
    "بعض الأمور تتحسن تدريجياً مع الوقت. 🌿",
    "الصعوبات جزء من الطريق وليست نهايته. 🛤️",
    "خذ الأمور كما تأتي، خطوة خطوة. 👣",
    "قد يكون اليوم أفضل مما تتوقع. ☀️",
    "كل صباح فرصة لتجربة جديدة. 🌅",
    "لا بأس أن تتقدم بالسرعة التي تناسبك. 🌱",
    "كل لحظة هدوء تستحق التقدير. 🍃",
    "يمكنك أن تفتخر بكل محاولة صادقة. ⭐",
    "أحياناً يكون الاستمرار أعظم إنجاز. 🌿",
    "كل يوم يمنحك فرصة أخرى للمحاولة. 🌷",
    "الطريق الطويل لا يُقطع دفعة واحدة. 🚶",
    "لا تحرم نفسك من الراحة عندما تحتاجها. 🌸",
    "التغيير يبدأ بخطوات بسيطة ومتكررة. ✨",
    "من الطبيعي أن تمر بأيام متفاوتة. 🌤️",
    "أعطِ نفسك الوقت الكافي للنمو. 🌱",
    "قد تجد القوة في أماكن لم تتوقعها. ⭐",
    "لا بأس أن تتوقف قليلاً ثم تواصل. 🌿",
    "كل فرصة جديدة تستحق أن تُمنح لنفسك. 🌅",
    "الأمل قد يعود عندما لا تتوقعه. ✨",
    "الاستمرار أهم من الوصول بسرعة. 🛤️",
    "كل يوم فرصة للاهتمام بنفسك أكثر. 🌷",
    "لا تنسَ تقدير الجهد الذي تبذله. 🤍",
    "بعض الخطوات الهادئة تغيّر الكثير مع الوقت. 🍃",
    "يمكنك أن تبدأ مرة أخرى دائماً. 🌄",
    "كل صباح يحمل احتمالاً جديداً. ☀️",
    "الصبر مع النفس شكل من أشكال العناية بها. 🌱",
    "لا بأس أن يكون يومك بسيطاً وهادئاً. 🌸",
    "كل خطوة واعية تستحق الاحترام. 👣",
    "الأيام الصعبة تمر كما مرت غيرها. 🌤️",
    "تذكر أن تمنح نفسك بعض اللطف اليوم. 🤍",
    "ما زالت أمامك فرص كثيرة لم تأتِ بعد. ✨",
    "كل يوم جديد هدية تستحق أن تعاش. 🌅",
    "كل فجر جديد يحمل فرصة جديدة للمحاولة. 🌅",
    "يكفي اليوم أن تخطو خطوة واحدة إلى الأمام. 👣",
    "لا بأس أن تسير ببطء ما دمت مستمراً. 🌱",
    "امنح نفسك بعض الرفق في هذا اليوم. 🌸",
    "كل جهد تبذله له قيمة حتى لو لم تلاحظها الآن. ⭐",
    "خذ وقتك، فالأشياء الجيدة تنمو بهدوء. 🌿",
    "كل يوم فرصة لتخفيف عبء صغير عن قلبك. 🤍",
    "التقدم لا يحتاج إلى الكمال. ✨",
    "كل بداية بسيطة تستحق الاحترام. 🌄",
    "الأمل قد يبدأ بفكرة صغيرة جداً. 🌱",
    "لا تحمل نفسك أكثر مما تستطيع اليوم. 🍃",
    "كل خطوة هادئة تقربك من هدفك. 🚶",
    "الصبر على النفس من أجمل أنواع القوة. 🌿",
    "يمكنك البدء من جديد متى احتجت لذلك. 🌅",
    "كل يوم يمنحك فرصة مختلفة للنمو. 🌱",
    "لا بأس أن يكون إنجاز اليوم هو الاستمرار فقط. 🤍",
    "بعض التقدم لا يُرى لكنه يحدث بالفعل. ✨",
    "امنح نفسك فرصة للهدوء وسط الزحام. 🕊️",
    "الأمور تتغير مع الوقت أكثر مما نظن. 🌤️",
    "كل صباح صفحة جديدة لم تُكتب بعد. ☀️",
    "يكفي أنك ما زلت تحاول. ⭐",
    "لا تنسَ أن تعتني بنفسك كما تعتني بغيرك. 🌸",
    "كل يوم جديد يحمل احتمالاً جميلاً. 🌄",
    "خذ الأمور خطوة خطوة ولا تستعجل الطريق. 👣",
    "الاستمرار الهادئ يصنع فرقاً كبيراً مع الوقت. 🌱",
    "من حقك أن تبحث عما يمنحك الراحة. 🌷",
    "كل محاولة جديدة تستحق التقدير. 🌟",
    "لا بأس أن تتوقف قليلاً لتستعيد طاقتك. 🌿",
    "الأمل لا يختفي لمجرد أنه تأخر. ✨",
    "كل يوم فرصة لتتعلم شيئاً جديداً عن نفسك. 📖",
    "قد يكون الغد ألطف مما تتوقع. ☀️",
    "لا تقارن رحلتك بأحد، فلها ظروفها الخاصة. 🛤️",
    "كل خطوة صغيرة لها أثرها. 👣",
    "أعطِ نفسك الوقت الذي تحتاجه. ⏳",
    "بعض الإنجازات تبدأ بقرار بسيط جداً. 🌱",
    "الهدوء أحياناً أفضل هدية تقدمها لنفسك. 🕊️",
    "كل يوم تعبره هو خبرة جديدة. 🌄",
    "لا بأس أن يكون التقدم بطيئاً. 🌿",
    "استمر في المحاولة، فهذا بحد ذاته إنجاز. ⭐",
    "كل صباح فرصة لبداية مختلفة. 🌅",
    "الأيام المتعبة لا تدوم للأبد. 🌤️",
    "امنح نفسك بعض التقدير على جهودك. 🤍",
    "كل خطوة نحو العناية بنفسك مهمة. 🌸",
    "قد تنمو الأشياء الجميلة بصمت. 🌱",
    "خذ استراحة عندما تحتاجها دون تردد. 🌷",
    "كل فرصة جديدة تستحق أن تُمنح لنفسك. ✨",
    "من الطبيعي أن تختلف طاقتك من وقت لآخر. 🌿",
    "التقدم الحقيقي يحدث خطوة بعد خطوة. 🚶",
    "كل يوم يحمل شيئاً يمكن الامتنان له. 🤍",
    "لا بأس أن تبدأ من جديد أكثر من مرة. 🌄",
    "الأمل قد يعود من حيث لا تتوقع. ✨",
    "كل محاولة صادقة تستحق الاحترام. ⭐",
    "امنح نفسك مساحة للتنفس والهدوء. 🍃",
    "الصعوبات جزء من الرحلة وليست الرحلة كلها. 🛤️",
    "كل يوم فرصة لتكون ألطف مع نفسك. 🌸",
    "لا تحتاج إلى إنجاز كل شيء اليوم. 🌱",
    "بعض التغييرات تحتاج إلى وقت وصبر. 🌿",
    "كل خطوة للأمام تستحق الاحتفال. 🎉",
    "استمع إلى احتياجاتك باهتمام. 🤍",
    "كل صباح يمنحك فرصة جديدة للمحاولة. ☀️",
    "لا بأس أن تطلب الدعم عند الحاجة. 🤝",
    "التعافي رحلة لها إيقاعها الخاص. 🌷",
    "كل يوم جديد يحمل فرصة للنمو. 🌱",
    "الأمور تتحسن أحياناً تدريجياً دون أن ننتبه. ✨",
    "أعطِ نفسك الإذن بالراحة عندما تحتاجها. 🌸",
    "كل لحظة هدوء لها قيمتها. 🕊️",
    "قد يكون أبسط تقدم هو الأهم. 👣",
    "لا تنسَ أن تلاحظ ما أنجزته بالفعل. ⭐",
    "كل فرصة جديدة تستحق المحاولة. 🌄",
    "الصبر يساعد على عبور الأيام الثقيلة. 🌿",
    "كل يوم تعيشه يضيف إلى خبرتك. 📖",
    "لا بأس أن تأخذ الأمور على مهل. 🌱",
    "الأمل قد يكبر مع كل خطوة صغيرة. ✨",
    "كل صباح فرصة لفتح صفحة جديدة. 🌅",
    "يكفي أن تفعل ما تستطيع فعله اليوم. 🤍",
    "لا تقلل من قيمة الجهود الصغيرة. 🌸",
    "كل خطوة واعية تقود إلى فرق حقيقي. 🚶",
    "من الطبيعي أن تحتاج إلى وقت إضافي أحياناً. 🌷",
    "كل يوم فرصة جديدة للعناية بنفسك. 🌿",
    "قد تكون أقرب إلى هدفك مما تعتقد. ⭐",
    "امنح نفسك بعض الصبر والرفق. 🌱",
    "كل بداية جديدة تحمل أملاً جديداً. 🌄",
    "الأيام تتغير، وكذلك الأحوال. 🌤️",
    "كل خطوة صغيرة تستحق أن تُحسب. 👣",
    "لا بأس أن يكون يومك هادئاً وبسيطاً. 🍃",
    "استمر، فالتقدم لا يحدث دفعة واحدة. 🌿",
    "كل صباح يحمل إمكانية جديدة. ☀️",
    "الأمل موجود حتى في البدايات الصغيرة. ✨",
    "تذكر أن تمنح نفسك بعض اللطف اليوم. 🤍",
    "كل يوم جديد فرصة أخرى للمضي قدماً. 🌅",
    "ما زالت أمامك فرص كثيرة لم تأتِ بعد. 🌟",
]

class FakeUpdate:
    def __init__(self, message):
        self.message = message
        self.effective_chat = message.chat
        self.effective_user = message.from_user

async def callback_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    msg = query.message
    chat_id = msg.chat.id

    if data == "menu_close":
        await msg.delete()
        return

    if data == "exec_stats":
        try:
            members_count = await context.bot.get_chat_member_count(chat_id)
            admins = await context.bot.get_chat_administrators(chat_id)
            admins_count = len(admins)
            await msg.reply_text(f"📊 إحصائيات المجموعة:\n👥 الأعضاء: {members_count}\n👮 المشرفون: {admins_count}")
        except:
            await msg.reply_text("📊 لا يمكن جلب الإحصائيات حالياً.")
        return

    if data == "exec_quote":
        await msg.reply_text(f"💬 اقتباس اليوم:\n\n{random.choice(DAILY_QUOTES)}")
        return

    if data == "menu_help":
        help_text = (
            "❓ **أوامر البوت**\n\n"
            "/start - إظهار القائمة\n"
            "/id - معرفك\n"
            "/rules - عرض القواعد\n"
            "/report - تقرير للمشرفين\n"
            "/ban @username - حظر\n"
            "/unban @username - رفع الحظر\n"
            "/mute @username - كتم\n"
            "/unmute @username - رفع الكتم\n"
            "يمكنك استخدام الأزرار للتنقل."
        )
        await msg.reply_text(help_text, parse_mode="Markdown")
        return

    if data == "menu_contact":
        await msg.reply_text("📞 **تواصل مع المطور:**\n[اضغط هنا](https://t.me/Me8dad)", parse_mode="Markdown", disable_web_page_preview=True)
        return

    if data == "menu_games":
        keyboard = [
            [InlineKeyboardButton("🎲 تخمين رقم (1-10)", callback_data="game_guess")],
            [InlineKeyboardButton("✂️ حجر ورقة مقص", callback_data="game_rps")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("🎮 **اختر لعبة:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "game_guess":
        number = random.randint(1, 10)
        temp_games[user.id] = number
        buttons = [[InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1,6)],
                   [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(6,11)]]
        await msg.reply_text("🎲 خمن الرقم (1-10):", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("guess_"):
        guessed = int(data.split("_")[1])
        correct = temp_games.get(user.id)
        if not correct:
            await query.answer("ابدأ لعبة جديدة من القائمة أولاً", show_alert=True)
            return
        if guessed == correct:
            await msg.reply_text(f"🎉 **صحيح!** الرقم كان {correct}. تهانينا!")
            del temp_games[user.id]
        else:
            await msg.reply_text(f"❌ خطأ! الرقم {guessed} ليس صحيحًا. حاول مرة أخرى.")
        return

    if data == "game_rps":
        keyboard = [
            [InlineKeyboardButton("🗻 حجر", callback_data="rps_rock")],
            [InlineKeyboardButton("📄 ورقة", callback_data="rps_paper")],
            [InlineKeyboardButton("✂️ مقص", callback_data="rps_scissors")],
        ]
        await msg.reply_text("اختر:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("rps_"):
        choice = data.split("_")[1]
        bot_choice = random.choice(['rock', 'paper', 'scissors'])
        choices_map = {'rock':'🗻 حجر', 'paper':'📄 ورقة', 'scissors':'✂️ مقص'}
        user_choice_text = choices_map.get(choice, choice)
        bot_choice_text = choices_map.get(bot_choice, bot_choice)
        if choice == bot_choice:
            result = "🤝 تعادل"
        elif (choice == 'rock' and bot_choice == 'scissors') or \
             (choice == 'scissors' and bot_choice == 'paper') or \
             (choice == 'paper' and bot_choice == 'rock'):
            result = "🎉 فزت!"
        else:
            result = "💔 خسرت!"
        await msg.reply_text(f"اخترت: {user_choice_text}\nالبوت اختار: {bot_choice_text}\n\n{result}")
        return

    if data == "menu_google":
        context.user_data['waiting_google'] = chat_id
        await msg.reply_text("🔍 **أرسل ما تريد البحث عنه في جوجل:**", parse_mode="Markdown")
        return

    # ================= قائمة الأوامر المتقدمة =================
    if data == "menu_commands":
        keyboard = [
            [InlineKeyboardButton("🔐 أوامر القفل والفتح", callback_data="menu_lock_commands")],
            [InlineKeyboardButton("🛠 الأوامر الخدمية", callback_data="menu_service_commands")],
            [InlineKeyboardButton("👮 أوامر الإدارة", callback_data="menu_admin_commands")],
            [InlineKeyboardButton("👨‍💻 أوامر المطور", callback_data="menu_dev_commands")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("📋 قائمة الأوامر المتخصصة:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_lock_commands":
        lock_types = [
            "links", "tags", "media", "files", "video", "voice", "gifs",
            "edit", "editmedia", "repeat", "join", "forward", "id", "badwords",
            "spam", "replies", "notifications", "persian", "bots", "iranian",
            "longtext", "quran", "porn", "ai", "autoreply", "games", "marketnews", "whisper"
        ]
        name_map = {
            "links":"الروابط", "tags":"التاك", "media":"الميديا", "files":"الملفات",
            "video":"الفيديو", "voice":"الفويسات", "gifs":"المتحركات", "edit":"التعديل",
            "editmedia":"تعديل الميديا", "repeat":"التكرار", "join":"الدخول", "forward":"التوجيه",
            "id":"ايدي", "badwords":"السب", "spam":"السبام", "replies":"الردود",
            "notifications":"الاشعارات", "persian":"الفارسية", "bots":"البوتات", "iranian":"دخول الايراني",
            "longtext":"الكلام الكثير", "quran":"القرآن", "porn":"الاباحي", "ai":"الذكاء الاصطناعي",
            "autoreply":"الرد التلقائي", "games":"الألعاب", "marketnews":"اخبار السوق", "whisper":"الهمسة"
        }
        buttons = []
        for lt in lock_types:
            display = name_map.get(lt, lt)
            buttons.append([InlineKeyboardButton(f"🔒 قفل {display}", callback_data=f"lock_{lt}"),
                            InlineKeyboardButton(f"🔓 فتح {display}", callback_data=f"unlock_{lt}")])
        buttons.append([InlineKeyboardButton("🔒 قفل الكل", callback_data="lock_all"),
                        InlineKeyboardButton("🔓 فتح الكل", callback_data="unlock_all")])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands")])
        buttons.append([InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")])
        await msg.edit_text("🔐 اختر نوع القفل:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("lock_") and not data.startswith("lock_all"):
        lock_type = data.split("_")[1]
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        await db.set_lock(chat_id, lock_type, True)
        await query.answer(f"🔒 تم قفل {lock_type}", show_alert=True)
        await msg.edit_text(f"🔒 تم قفل {lock_type}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_lock_commands")]]))
        return
    if data.startswith("unlock_") and not data.startswith("unlock_all"):
        lock_type = data.split("_")[1]
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        await db.set_lock(chat_id, lock_type, False)
        await query.answer(f"🔓 تم فتح {lock_type}", show_alert=True)
        await msg.edit_text(f"🔓 تم فتح {lock_type}.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_lock_commands")]]))
        return

    if data == "lock_all":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        lock_types = ["links","tags","media","files","video","voice","gifs","edit","editmedia","repeat","join","forward","id","badwords","spam","replies","notifications","persian","bots","iranian","longtext","quran","porn","ai","autoreply","games","marketnews","whisper"]
        for lt in lock_types:
            await db.set_lock(chat_id, lt, True)
        await query.answer("🔒 تم قفل جميع الحمايات", show_alert=True)
        await msg.edit_text("🔒 تم قفل كل شيء.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_lock_commands")]]))
        return
    if data == "unlock_all":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        lock_types = ["links","tags","media","files","video","voice","gifs","edit","editmedia","repeat","join","forward","id","badwords","spam","replies","notifications","persian","bots","iranian","longtext","quran","porn","ai","autoreply","games","marketnews","whisper"]
        for lt in lock_types:
            await db.set_lock(chat_id, lt, False)
        await query.answer("🔓 تم فتح جميع الحمايات", show_alert=True)
        await msg.edit_text("🔓 تم فتح كل شيء.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_lock_commands")]]))
        return

    if data == "menu_service_commands":
        text = (
            "🛠 **الأوامر الخدمية:**\n"
            "• ايدي - معرفك\n"
            "• افتاري - رابط المجموعة\n"
            "• اهمس @username - رسالة خاصة\n"
            "• صارحني - رابط لرسائل مجهولة\n"
            "• سورة [رقم السورة] - معلومات السورة\n"
            "• المالك - تواصل مع المطور"
        )
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands")]]))
        return

    if data == "menu_admin_commands":
        text = (
            "👮 **أوامر الإدارة (للمشرفين):**\n"
            "• كتم / الغاء كتم\n"
            "• طرد / حظر / الغاء حظر\n"
            "• رفع مشرف / تنزيل مشرف\n"
            "• رفع / تنزيل (عضو مميز)\n"
            "• المشرفين / تنزيل الكل\n"
            "• مسح [عدد] / مسح المحظورين\n"
            "• مسح المكتومين / تاك للكل\n"
            "• رتبتي / رتبته"
        )
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands")]]))
        return

    if data == "menu_dev_commands":
        text = (
            "👨‍💻 **أوامر المطور:**\n"
            "• رفع مطور / تنزيل مطور\n"
            "• اضف مطور / حذف مطور\n"
            "• المطور / اذاعه"
        )
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="menu_commands")]]))
        return

    # ================= القوائم الرئيسية =================
    if data == "menu_main":
    keyboard = [
        [InlineKeyboardButton("👮 أوامر المشرفين", callback_data="menu_admin")],
        [InlineKeyboardButton("👥 للجميع", callback_data="menu_user")],
        [InlineKeyboardButton("🎵 الميديا", callback_data="menu_media")],
        [InlineKeyboardButton("📚 الموارد", callback_data="menu_resources")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="exec_stats")],
        [InlineKeyboardButton("💬 اقتباس اليوم", callback_data="exec_quote")],
        [InlineKeyboardButton("📋 الأوامر", callback_data="menu_commands")],
        [InlineKeyboardButton("❓ المساعدة", callback_data="menu_help")],
        [InlineKeyboardButton("📞 تواصل", callback_data="menu_contact")],
        [InlineKeyboardButton("🎮 ألعاب", callback_data="menu_games")],
        [InlineKeyboardButton("🔍 بحث جوجل", callback_data="menu_google")],
        [InlineKeyboardButton("📢 قناة تحديثات شفق", url="https://t.me/shafaqmeqdad")],
        [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
    ]
    await msg.edit_text("🌅 بوت شفق — القائمة الرئيسية\nاختر القسم:", reply_markup=InlineKeyboardMarkup(keyboard))
    return
    if data == "menu_admin":
        keyboard = [
            [InlineKeyboardButton("🚫 الحظر", callback_data="menu_ban")],
            [InlineKeyboardButton("⚠️ التحذيرات", callback_data="menu_warn")],
            [InlineKeyboardButton("🔇 الكتم", callback_data="menu_mute")],
            [InlineKeyboardButton("⚙️ الإدارة", callback_data="menu_manage")],
            [InlineKeyboardButton("🔗 رابط دعوة", callback_data="exec_invite")],
            [InlineKeyboardButton("🗑️ مسح رسائل", callback_data="exec_purge")],
            [InlineKeyboardButton("📢 بث", callback_data="exec_broadcast")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("👮 أوامر المشرفين — اختر:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_ban":
        keyboard = [
            [InlineKeyboardButton("📋 قائمة المحظورين", callback_data="exec_banlist")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "🚫 **الحظر:**\n• حظر — رد على عضو\n• حظر 123 7d سبب — حظر مؤقت\n• رفع الحظر — رد على عضو\n• تحقق — رد على عضو\n• معلومات — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_warn":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "⚠️ **التحذيرات:**\n• تحذير — رد على عضو\n• مسح التحذير — رد على عضو\n• التحذيرات — رد على عضو\n\nملاحظة: 3 تحذيرات = حظر تلقائي",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_mute":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "🔇 **الكتم:**\n• كتم — رد على عضو\n• كتم 123 1h — كتم مؤقت\n• رفع الكتم — رد على عضو",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_manage":
        keyboard = [
            [InlineKeyboardButton("🔒 أغلق المجموعة", callback_data="exec_lock")],
            [InlineKeyboardButton("🔓 افتح المجموعة", callback_data="exec_unlock")],
            [InlineKeyboardButton("📋 سجل الأحداث", callback_data="exec_eventlog")],
            [InlineKeyboardButton("📊 تقرير فوري", callback_data="exec_report")],
            [InlineKeyboardButton("🚫 الكلمات المحظورة", callback_data="exec_wordlist")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_admin")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("⚙️ الإدارة — اختر أمراً:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "menu_user":
        keyboard = [
            [InlineKeyboardButton("🪪 معلوماتي", callback_data="exec_id")],
            [InlineKeyboardButton("📋 القواعد", callback_data="exec_rules")],
            [InlineKeyboardButton("📚 الموارد", callback_data="exec_resources")],
            [InlineKeyboardButton("📈 إحصائياتي", callback_data="exec_member_stats")],
            [InlineKeyboardButton("🎁 هدية عشوائية", callback_data="exec_gift")],
            [InlineKeyboardButton("🌐 ترجمة", callback_data="exec_translate")],
            [InlineKeyboardButton("⏰ تذكير", callback_data="exec_remind")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text("👥 للجميع — اختر أمراً:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "exec_id":
        first = user.first_name or ""
        username = f"@{user.username}" if user.username else ""
        await msg.reply_text(f"🪪 **معلوماتك:**\nالاسم: {first}\nالمعرف: {user.id}\n{username}", parse_mode="Markdown")
        return

    if data == "exec_rules":
        rules = await db.get_setting(chat_id, "rules")
        if rules:
            await msg.reply_text(f"📋 **قواعد المجموعة:**\n{rules}", parse_mode="Markdown")
        else:
            await query.answer("لم يتم تعيين قواعد بعد", show_alert=True)
        return

    if data == "exec_resources":
        from handlers_resources import _get_resources
        resources = await _get_resources(chat_id)
        if not resources:
            await query.answer("لا توجد موارد مضافة بعد", show_alert=True)
            return
        lines = []
        for i, r in enumerate(resources[:20], 1):
            lines.append(f"{i}. 📌 {r['title']}\n   {r['content'][:100]}")
        await msg.reply_text("📚 **الموارد:**\n\n" + "\n\n".join(lines), parse_mode="Markdown")
        return

    if data == "exec_member_stats":
        points = temp_points.get(user.id, 0)
        await msg.reply_text(f"📈 **إحصائياتك:**\nعدد النقاط: {points}\n(يمكنك كسب نقطة عبر 'هدية عشوائية')", parse_mode="Markdown")
        return

    if data == "exec_gift":
        gift = random.randint(1, 10)
        temp_points[user.id] = temp_points.get(user.id, 0) + gift
        await msg.reply_text(f"🎁 **لقد حصلت على {gift} نقطة!**\nإجمالي نقاطك: {temp_points[user.id]}", parse_mode="Markdown")
        return

    if data == "exec_translate":
        await msg.reply_text("🌐 **أرسل النص الذي تريد ترجمته إلى العربية:**", parse_mode="Markdown")
        context.user_data['waiting_translate'] = chat_id
        return

    if data == "exec_remind":
        await msg.reply_text("⏰ **أرسل عدد الدقائق ثم نص التذكير (مثال: 5 تذكير بالاجتماع)**", parse_mode="Markdown")
        context.user_data['waiting_remind'] = chat_id
        return

    if data == "menu_media":
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "🎵 **الميديا:**\n• أرسل رابط يوتيوب / تيك توك / انستقرام مباشرة\n• يوتيوب <اسم الأغنية> — بحث",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "menu_resources":
        keyboard = [
            [InlineKeyboardButton("📖 عرض الموارد", callback_data="exec_resources")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu_main")],
            [InlineKeyboardButton("❌ إغلاق", callback_data="menu_close")],
        ]
        await msg.edit_text(
            "📚 **الموارد:**\n• الموارد — عرض القائمة\n• الموارد <كلمة> — بحث",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    if data == "exec_banlist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        bans = await db.get_ban_list(chat_id)
        if not bans:
            await query.answer("لا يوجد محظورون حالياً ✅", show_alert=True)
            return
        lines = [f"• {b['user_id']}" + (f" (ينتهي {b['expires_at'][:10]})" if b.get('expires_at') else " (دائم)") for b in bans[:20]]
        await msg.reply_text("🚫 **المحظورون:**\n" + "\n".join(lines), parse_mode="Markdown")
        return

    if data == "exec_lock":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        try:
            await context.bot.set_chat_permissions(chat_id, permissions=ChatPermissions(can_send_messages=False))
            await query.answer("🔒 تم إغلاق المجموعة", show_alert=True)
            await db.log_event(chat_id, "lock", user_id=user.id)
        except:
            await query.answer("❌ تعذّر الإغلاق", show_alert=True)
        return

    if data == "exec_unlock":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        try:
            await context.bot.set_chat_permissions(chat_id, permissions=ChatPermissions(
                can_send_messages=True, can_send_media_messages=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True))
            await query.answer("🔓 تم فتح المجموعة", show_alert=True)
            await db.log_event(chat_id, "unlock", user_id=user.id)
        except:
            await query.answer("❌ تعذّر الفتح", show_alert=True)
        return

    if data == "exec_eventlog":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        events = await db.get_event_log(chat_id, 10)
        if not events:
            await query.answer("لا توجد أحداث مسجلة", show_alert=True)
            return
        lines = [f"• {e['action']} — {e['created_at'][:16]}" for e in events]
        await msg.reply_text("📋 **سجل الأحداث:**\n" + "\n".join(lines))
        return

    if data == "exec_wordlist":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        words = await db.get_banned_words(chat_id)
        if not words:
            await query.answer("لا توجد كلمات محظورة", show_alert=True)
            return
        await msg.reply_text("🚫 **الكلمات المحظورة:**\n" + "\n".join(f"• {w}" for w in words))
        return

    if data == "exec_report":
        try:
            member = await context.bot.get_chat_member(chat_id, user.id)
            if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR):
                await query.answer("⛔ هذا الأمر للمشرفين فقط.", show_alert=True)
                return
        except Exception as e:
            logger.error(f"خطأ في التحقق من صلاحية التقرير: {e}")
            await query.answer("⛔ لا يمكن التحقق من صلاحيتك.", show_alert=True)
            return
        from handlers_jobs import cmd_report
        fake_update = FakeUpdate(msg)
        context.args = []
        await cmd_report(fake_update, context)
        return

    if data == "exec_invite":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        try:
            link = await context.bot.create_chat_invite_link(chat_id, member_limit=1)
            await msg.reply_text(f"🔗 **رابط دعوة:** {link.invite_link}", parse_mode="Markdown")
        except:
            await query.answer("❌ لا يمكن إنشاء رابط، تأكد من صلاحيات البوت.", show_alert=True)
        return

    if data == "exec_purge":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        await msg.reply_text("📨 **أرسل عدد الرسائل أو رد على رسالة لمسح كل الرسائل بعدها.**", parse_mode="Markdown")
        context.user_data['purge_mode'] = chat_id
        return

    if data == "exec_broadcast":
        if not await is_admin(update, context):
            await query.answer("⛔ للمشرفين فقط", show_alert=True)
            return
        await msg.reply_text("📢 **أرسل النص الذي تريد بثه للمجموعة:**", parse_mode="Markdown")
        context.user_data['waiting_broadcast'] = chat_id
        return