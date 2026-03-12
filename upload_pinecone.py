"""
UPLOAD BENEFICIOS A PINECONE
==============================
Vectoriza y sube todos los beneficios al índice Pinecone
"""
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_HOST = os.getenv("PINECONE_HOST")
INDEX_NAME = os.getenv("PINECONE_INDEX", "api-rag-mvp")
NAMESPACE = "beneficios-bancarios"
BATCH_SIZE = 50


def beneficio_to_text(b: dict) -> str:
    """Convierte un beneficio a texto para embedding"""
    dias = ", ".join(b.get("dias_validos", []))
    return (
        f"{b['restaurante']} - {b['banco']} - {b['descuento_texto']} - "
        f"Días: {dias} - {b.get('ubicacion', '')} - "
        f"{b.get('restricciones_texto', '')}"
    ).strip()


def main():
    print("🚀 Subiendo beneficios a Pinecone...")

    # Cargar beneficios
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "beneficios.json")

    with open(json_path, "r", encoding="utf-8") as f:
        beneficios = json.load(f)

    print(f"📦 {len(beneficios)} beneficios cargados")

    # Inicializar clientes
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME, host=f"https://{PINECONE_HOST}")

    # Borrar namespace anterior si existe
    try:
        index.delete(delete_all=True, namespace=NAMESPACE)
        print("🗑️  Namespace anterior limpiado")
    except Exception:
        pass

    # Procesar en lotes
    total_subidos = 0
    for i in range(0, len(beneficios), BATCH_SIZE):
        batch = beneficios[i : i + BATCH_SIZE]
        textos = [beneficio_to_text(b) for b in batch]

        # Generar embeddings
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=textos,
        )

        # Preparar vectores
        vectors = []
        for j, (b, emb) in enumerate(zip(batch, response.data)):
            vectors.append(
                {
                    "id": b["id"],
                    "values": emb.embedding,
                    "metadata": {
                        "restaurante": b["restaurante"],
                        "banco": b["banco"],
                        "descuento_texto": b["descuento_texto"],
                        "descuento_valor": b.get("descuento_valor", 0),
                        "dias_validos": ", ".join(b.get("dias_validos", [])),
                        "ubicacion": b.get("ubicacion", ""),
                        "restricciones_texto": b.get("restricciones_texto", ""),
                        "presencial": b.get("presencial", True),
                    },
                }
            )

        # Upsert
        index.upsert(vectors=vectors, namespace=NAMESPACE)
        total_subidos += len(vectors)
        print(f"   ✅ {total_subidos}/{len(beneficios)} vectores subidos")

    # Verificar
    stats = index.describe_index_stats()
    ns_stats = stats.get("namespaces", {}).get(NAMESPACE, {})
    print(f"\n✅ COMPLETADO: {ns_stats.get('vector_count', total_subidos)} vectores en Pinecone")
    print(f"   Index: {INDEX_NAME}")
    print(f"   Namespace: {NAMESPACE}")


if __name__ == "__main__":
    main()
