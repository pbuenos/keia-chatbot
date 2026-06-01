from pathlib import Path
import pandas as pd
import unicodedata
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent



app = Flask(__name__)
CORS(app)

#normalizo el csv, sirve por si quieren escalarlo a automatizacion con busqueda real
def normalizar(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(texto).lower().strip())
        if unicodedata.category(c) != 'Mn'
    )

csv_path = BASE_DIR / "ia_data.csv"
df = pd.read_csv(csv_path)
df = df.applymap(normalizar)
df["score"] = df["score"].astype(int)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():    

    data = request.json
    mensaje = normalizar(data.get("mensaje", ""))
    estado = data.get("estado", {})
    mensaje_limpio = mensaje.split("(")[0].strip().lower()


    paso = estado.get("paso", 1)

    if paso == 1 and not estado:
        return jsonify({
            "respuesta": "¡Hola! KeIA te ayuda a encontrar la mejor IA 😄 ¿Qué rubro te interesa?",
            "opciones": ["Programacion", "Diseño", "Escritura"],
            "estado": {"paso": 1}
        })
            

    if paso == 1:
        estado["rubro"] = mensaje

        return jsonify({
            "respuesta": "¿Qué nivel buscas?",
            "opciones": ["Principiante", "Avanzado"],
            "estado": estado | {"paso": 2}
        })

    elif paso == 2:
        estado["nivel"] = mensaje
        
        resultado = df[
            (df["rubro"] == estado["rubro"])
        ]        
    
        return jsonify({
            "respuesta": "¿Qué plan preferís?",
            "opciones": ["Gratuito", "Premium"],
            "estado": estado | {"paso": 3}
        })

    elif paso == 3:
        estado["plan"] = mensaje

        resultado = df[
            (df["rubro"] == estado["rubro"]) &
            (df["nivel"] == estado["nivel"])
        ]      
           
        return jsonify({
            "respuesta": "¿Qué prioridad buscas?",
            "opciones": ["Facilidad", "Profesional", "Velocidad"],
            "estado": estado | {"paso": 4}
        })
    

    elif paso == 4:

        estado["prioridad"]= mensaje

        resultado = df[
            (df["rubro"] == estado["rubro"]) &
            (df["nivel"] == estado["nivel"]) &
            (df["plan"] == estado["plan"]) &
            (df["prioridad"] == estado["prioridad"])
        ]

        if resultado.empty:
            return jsonify({
                "respuesta": "No encontré una IA para esos criterios.",
                "estado": {"paso": 1}
            })

        ranking_ordenado = resultado.sort_values("score", ascending=False)

        max_score = ranking_ordenado.iloc[0]["score"]

        empatadas = ranking_ordenado[ranking_ordenado["score"] == max_score]

        # En caso de empate de scores
        if len(empatadas) > 1:
            estado["paso"] = 5
            estado["opciones_empate"] = empatadas.to_dict(orient="records")

            return jsonify({
                "respuesta": "Hay un empate entre varias IAs. Elegí una o seguí buscando:",
                "opciones": [
                    f"{row['recomendacion']} ({row['score']})"
                    for _, row in empatadas.iterrows()
                ] + ["Buscar otra IA", "Finalizar"]
            })

        # Sin empate de scores  
        mejor = ranking_ordenado.iloc[0]

        fuente = mejor["fuente_ia"]
        recomendacion = mejor["recomendacion"]
        puntaje = mejor["score"]
        link = mejor["link"]

        ranking_texto = "\n".join(
            f"{row['fuente_ia']} recomienda {row['recomendacion']} → {row['score']} puntos"
            for _, row in ranking_ordenado.iterrows()
        )

        return jsonify({
            "respuesta": (
                f"Mejor recomendación (generada por {fuente}): {recomendacion} "
                f"({puntaje} puntos)\n\n"
                f"Ranking completo:\n{ranking_texto}"
            ),
            "link": link,
            "opciones": [
               "Buscar otra IA",
                "Finalizar"                             
            ],
            "estado": {"paso": 6}
        })    
       

    elif paso == 5:
        # buscar otra IA (reinicia todo)
        if "buscar otra ia" in mensaje_limpio:
            return jsonify({
                "respuesta": "Empecemos de nuevo 😊",
                "opciones": ["Programacion", "Diseño", "Escritura"],
                "estado": {"paso": 1}
            })
        

        # elección final del empate
        return jsonify({
            "respuesta": f"Perfecto 👍 elegiste {mensaje_limpio}. Esa será tu IA recomendada.",
            "estado": estado,
            "link": link
        })
    
    elif paso == 6:        

        if "buscar otra ia" in mensaje_limpio:
            return jsonify({
                "respuesta": "¡Genial! Empecemos otra vez 😄 ¿Qué rubro te interesa?",
                "opciones": ["Programacion", "Diseño", "Escritura"],
                "estado": {"paso": 1}
            })

        if "finalizar" in mensaje_limpio:
            return jsonify({
                "respuesta": "¡Gracias por usar KeIA! 👋",
                "opciones": [],
                "estado": {"paso": 6}
            })
        

if __name__ == "__main__":
    app.run(debug=True) 