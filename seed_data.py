"""
Script para poblar la base de datos con datos de ejemplo:
- Tendencias de mercado
- Referencias de competencia
- Embeddings para búsqueda RAG

Uso: python seed_data.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from shared_tools import (
    add_competitor_reference,
    add_trend,
    get_all_trends,
    get_all_competitors,
)
from shared_tools.db import execute_db


def seed_clientes():
    """Completa perfiles de prueba con contexto de marketing para Colombia."""
    print("═══ Poblando perfiles de clientes ═══")
    profiles = [
        (
            "EcoBrand",
            "Protector solar y cosmética natural con ingredientes de origen responsable.",
            "Personas de 18 a 35 años en Colombia interesadas en sostenibilidad y autocuidado.",
            "Aumentar reconocimiento y contenido compartible en Instagram y Facebook.",
            "Cuidado personal efectivo con transparencia y menor impacto ambiental.",
            "Educación, detrás de cámaras, sostenibilidad verificable y testimonios reales.",
            "Instagram, Facebook, TikTok",
            "No prometer protección absoluta ni afirmaciones médicas sin respaldo.",
        ),
        (
            "TechStart",
            "Aplicación móvil para recibir pagos y administrar ventas de pequeños negocios.",
            "Panaderías, cafeterías y comercios independientes de Colombia.",
            "Generar registros y demostrar que cobrar digitalmente es sencillo y seguro.",
            "Pagos rápidos y simples sin exigir conocimientos técnicos.",
            "Tutoriales, casos de clientes, datos y demostraciones de producto.",
            "Instagram, Facebook, LinkedIn",
            "No prometer aprobación financiera ni usar datos sin autorización.",
        ),
        (
            "FitLife",
            "Suplementos naturales y planes de entrenamiento personalizados.",
            "Adultos de 25 a 45 años en Colombia interesados en salud integral.",
            "Aumentar consideración de producto y participación en retos saludables.",
            "Acompañamiento personalizado basado en hábitos sostenibles y evidencia.",
            "Ciencia sencilla, comunidad, rutinas, hábitos y testimonios verificables.",
            "Instagram, Facebook, TikTok",
            "No prometer curas ni resultados garantizados.",
        ),
    ]
    for profile in profiles:
        execute_db(
            "UPDATE clientes SET producto_servicio=%s, audiencia_objetivo=%s, "
            "objetivo_marketing=%s, propuesta_valor=%s, pilares_contenido=%s, "
            "canales_objetivo=%s, pais='Colombia', zona_horaria='America/Bogota', "
            "restricciones_legales=%s WHERE nombre=%s",
            (*profile[1:], profile[0]),
        )
    print(f"  → {len(profiles)} perfiles preparados\n")


def seed_tendencias():
    print("═══ Poblando tendencias ═══")
    existing = get_all_trends(limit=1)
    if existing:
        print(f"  ✓ Ya hay {len(existing)}+ tendencias, omitiendo seed")
        return

    tendencias = [
        # Marketing
        ("marketing", "El contenido UGC (User Generated Content) crece un 45% en engagement vs contenido de marca", "interna"),
        ("marketing", "Los micro-influencers (1K-50K seguidores) generan 60% más engagement que las macro-celebridades", "interna"),
        ("marketing", "El storytelling auténtico y detrás de cámaras supera al contenido pulido en redes sociales", "interna"),
        ("marketing", "Los carruseles en Instagram tienen 3x más guardados que las publicaciones de imagen simple", "interna"),
        ("marketing", "El video corto vertical (<30 seg) domina TikTok e Instagram Reels con 78% de retención", "interna"),

        # Sostenibilidad
        ("sostenibilidad", "El 73% de los millennials está dispuesto a pagar más por productos sostenibles", "interna"),
        ("sostenibilidad", "Las marcas con certificaciones verificadas de sostenibilidad tienen 2.5x más confianza", "interna"),
        ("sostenibilidad", "El greenwashing detectado genera un 67% de pérdida de confianza a largo plazo", "interna"),

        # Tech/Fintech
        ("tech", "Los pagos con QR crecieron 300% en Latinoamérica durante 2025", "interna"),
        ("tech", "El 45% de las PYMEs latinas sigue usando efectivo como método principal", "interna"),
        ("tech", "La IA generativa en herramientas de productividad alcanzó 40% de adopción empresarial", "interna"),

        # Fitness/Salud
        ("fitness", "Los planes de entrenamiento personalizados con IA tienen 3x más retención a 90 días", "interna"),
        ("fitness", "El wellness mental se integra al fitness: 58% busca rutinas que incluyan mindfulness", "interna"),
        ("fitness", "Los suplementos naturales crecieron 25% en ventas online durante 2025", "interna"),

        # Social Media Trends
        ("social", "Las plataformas premian contenido nativo: compartir enlaces externos reduce alcance 40%", "interna"),
        ("social", "Los memes de marca auténticos generan 2x más shares que el contenido formal", "interna"),
        ("social", "LinkedIn Stories y newsletters son el formato B2B de mayor crecimiento en 2026", "interna"),
    ]

    count = 0
    for cat, content, fuente in tendencias:
        tid = add_trend(cat, content, fuente)
        if tid:
            count += 1
            print(f"  ✓ [{cat}] {content[:70]}…")
    print(f"  → {count} tendencias creadas con embeddings\n")


def seed_competencia():
    print("═══ Poblando referencias de competencia ═══")
    existing = get_all_competitors(limit=1)
    if existing:
        print(f"  ✓ Ya hay referencias, omitiendo seed")
        return

    refs = [
        # Competidores de EcoBrand
        ("Patagonia", "Campaña 'Don't Buy This Jacket': mensaje anti-consumo que generó fidelidad extrema de marca", "instagram"),
        ("Patagonia", "Series documentales sobre activismo ambiental en YouTube con millones de views orgánicas", "youtube"),
        ("The Body Shop", "Programa de refill/recarga en tiendas físicas que reduce plástico un 80%", "linkedin"),
        ("Lush", "Marketing sin embalaje: productos desnudos como diferenciador visual de marca", "instagram"),
        ("Who Gives A Papel", "Suscripción de papel higiénico con causa social: 1 donación por cada rollo", "tiktok"),

        # Competidores de TechStart
        ("Nubank", "Contenido educativo financiero en TikTok con lenguaje simple y memes", "tiktok"),
        ("Nubank", "UI/UX minimalista como diferenciador: 'la app que tu mamá puede usar'", "linkedin"),
        ("Mercado Pago", "Cashback instantáneo como hook de adquisición de nuevos usuarios", "instagram"),
        ("Wise", "Transparent pricing como mensaje central: 'sin comisiones ocultas'", "twitter"),

        # Competidores de FitLife
        ("MyProtein", "Precios agresivos + contenido educativo de suplementación en redes", "instagram"),
        ("Noom", "Gamificación del wellness: retos diarios con seguimiento de hábitos", "tiktok"),
        ("Peloton", "Comunidad como producto: clases en vivo con leaderboard social", "linkedin"),
        ("MyFitnessPal", "Datos personales como contenido: infografías de progreso de usuarios", "twitter"),
    ]

    count = 0
    for comp, content, plat in refs:
        rid = add_competitor_reference(comp, content, plat)
        if rid:
            count += 1
            print(f"  ✓ [{comp}] {content[:70]}…")
    print(f"  → {count} referencias creadas con embeddings\n")


if __name__ == "__main__":
    print("═══════════════════════════════════════")
    print(" Seed Data — Población de datos ejemplo")
    print("═══════════════════════════════════════\n")

    seed_clientes()
    seed_tendencias()
    seed_competencia()

    print("═══════════════════════════════════════")
    print(" ✅ Seed completado")
    print("═══════════════════════════════════════")
    print("\nPrueba ahora:")
    print("  python enviar_brief.py 'Campaña de navidad para tienda de ropa sostenible'")
