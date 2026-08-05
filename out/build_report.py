import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from curator.models import Post, RunResult
from curator import report

IMG = os.path.join(os.path.dirname(__file__), "images")

def post(handle, name, text, likes, rt, replies, views, img=None):
    p = Post(author_handle=handle, author_name=name, text=text, likes=likes,
             replies=replies, reposts=rt, timestamp="", permalink="",
             has_image=bool(img))
    if img:
        p.image_screenshot_paths = [os.path.join(IMG, img)]
    p.text = text + f"  ·  ({likes:,} likes · {rt:,} RT · {views} views)".replace(",", ".")
    return p

posts = [
    post("@nico_taglia", "Nico Tagliafico (jugador)",
         "Reacción del plantel: 'Duele mucho, no lo voy a negar. Pero haber llegado a otra final y dejar todo no lo borra nada. Orgulloso de este grupo. Gracias a todos los argentinos.' — La postura de aceptación digna, sin teorías.",
         268000, 23000, 12000, "2M"),
    post("@duarte_maxi", "Maxi Duarte",
         "Teoría geopolítica/Malvinas: vincula la derrota a un supuesto agravio histórico con Inglaterra ('si la de Malvinas nos sacó la final, igual somos los más grandes').",
         151000, 29000, 1100, "1M"),
    post("@KenjakuFan", "Kenjaku Argento",
         "Árbitro señalado: 'Los únicos 2 partidos que perdió la Scaloneta fueron con este árbitro, Slavko Vincic. Ni una tarjeta a España. Son unos chorros.' Acusa arbitraje sesgado.",
         95000, 12000, 5800, "1.6M", img="kenjaku-arbitro.png"),
    post("@mikemaquinadel", "Mike Maquina del Mal",
         "Autoironía / opinión escéptica: 'Todos los Mundiales están arreglados, menos los que ganamos nosotros — Un argentino.' Se burla del propio sesgo.",
         53000, 3600, 750, "463K"),
    post("@derechazoar", "Derechazo",
         "Presagio/conspiración: 'ELIJO CREER: la última vez que Argentina perdió una final del Mundial, el presidente de la AFA murió 17 días después.'",
         52000, 4900, 262, "900K"),
    post("@Uricarp91218", "Uricarp",
         "Arbitraje: polémica por la doble amarilla/expulsión a Enzo Fernández. 'Qué conveniente para decir que Argentina hace trampa solo para robarnos.'",
         31000, 2700, 1300, "446K"),
    post("@porqueTTarg", "Tendencias en Argentina",
         "Programación predictiva / 'masonería': afirma que el libro 'The World Game' (publicado 2/6/2026) ya 'predecía' que el 7 de España, Ferran Torres, marcaría en la final. TEORÍA sin pruebas.",
         20000, 1200, 151, "729K", img="porqueTTarg-worldgame.png"),
    post("@MotivacionesF", "Motivaciones Fútbol",
         "Petición formal: miles de aficionados firman para que la FIFA REPITA la final, alegando que debió arbitrarla otro árbitro.",
         8800, 4400, 13000, "2.5M"),
    post("@Messias30_", "Messias",
         "Numerología: 'Argentina hizo 19 goles y recibió 7; la final es el 19/7; Messi hizo 8 y la mitad de 8 es 4...'. Juego de números como 'señal'.",
         6800, 768, 126, "90K"),
    post("@marcalpalazzolo", "Marcos Palazzolo",
         "'Final regalada': 'Qué feo que te REGALEN un Mundial; ese España vs Argentina fue escandaloso, al punto que los jugadores no querían ni festejar.'",
         763, 140, 563, "15K"),
    post("@abc_es", "ABC.es (medio español)",
         "Cobertura de medio: reporta que aficionados denuncian una actuación 'polémica y corrupta' del árbitro, al que acusan (sin pruebas) de haber sido 'sobornado', y la campaña de firmas para repetir la final.",
         302, 292, 582, "173K", img="abc-repetir-final.png"),
    post("@DiarioOle", "Diario Olé (medio)",
         "Cobertura: miles de argentinos firman una campaña para pedir la revancha de la final contra España.",
         182, 120, 712, "48K", img="diarioOle-campana.png"),
    post("@MundoEConflicto", "Mundo en Conflicto",
         "Escándalo institucional: 'FIFA abre una investigación contra Argentina por la pelea que se desató tras el partido después de la derrota en la final.'",
         15000, 1200, 278, "315K"),
]

summary = (
    "Contexto: en la final del Mundial 2026, ESPAÑA venció 1-0 a ARGENTINA con un gol de "
    "Ferran Torres en tiempo extra. En el camino Argentina había eliminado a Inglaterra (2-1), "
    "dato que alimenta parte de las teorías. Tras la derrota, la conversación en X (POV Argentina) "
    "se dividió en varias corrientes de opinión:\n\n"
    "1) 'Nos robaron / mal arbitrada': el foco recae en el árbitro Slavko Vincic (acusaciones de "
    "sesgo y hasta de soborno, sin pruebas), la expulsión de Enzo Fernandez y una campaña masiva de "
    "firmas para que la FIFA repita la final.\n\n"
    "2) 'Final arreglada/regalada': afirman que a España 'le regalaron' el título y que el partido fue "
    "escandaloso.\n\n"
    "3) Teorías conspirativas fuertes: 'programación predictiva' (un libro, 'The World Game', que "
    "supuestamente predijo el gol del 7 de España), numerología (19 goles/7 recibidos, final 19/7), "
    "presagios (la muerte del presidente de la AFA tras una final perdida) y conexiones geopolíticas "
    "con Malvinas/Inglaterra. Son AFIRMACIONES sin evidencia, presentadas aquí como el discurso que "
    "circula, no como hechos.\n\n"
    "4) Escepticismo / autocrítica: cuentas argentinas se burlan del propio sesgo ('todos los mundiales "
    "están arreglados menos los que ganamos') y el jugador Nico Tagliafico representa la aceptación digna.\n\n"
    "5) Escándalo institucional real: se reporta que la FIFA habría abierto una investigación por una "
    "pelea posterior al partido.\n\n"
    "En conjunto: mucho dolor convertido en teoría del complot, un árbitro como villano central, una "
    "campaña de revancha, y una minoría que llama a aceptar la derrota."
)

run = RunResult(topic="Final Mundial 2026 Argentina vs Espana — escandalo y teorias (POV Argentina)",
                timestamp="2026-07-22", posts=posts, summary_text=summary,
                output_dir="out/report")
report.write_outputs(run, os.path.join(os.path.dirname(__file__), "report"))
print("wrote", len(posts), "posts")
