"""
Social Scheduler - Auto-publisher de entradas WordPress a redes sociales
Proyecto Delta (proyectodelta.eu)
"""

import os
import json
import re
import requests
from datetime import datetime, timezone
from pathlib import Path

# ─── Configuración ────────────────────────────────────────────────────────────

WP_API_URL    = "https://proyectodelta.eu/wp-json/wp/v2/posts"
PUBLISHED_LOG = Path(__file__).parent.parent / "published_posts.json"

CATEGORY_NAMES = {
    4:  "Divulgación",
    5:  "Observación",
    19: "Noticias",
}

# ─── Utilidades ───────────────────────────────────────────────────────────────

def clean_html(text: str) -> str:
    """Elimina etiquetas HTML y limpia el texto."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&#8230;", "…").replace("&amp;", "&")
    text = text.replace("&nbsp;", " ").replace("[…]", "…")
    return text.strip()


def load_published() -> set:
    if PUBLISHED_LOG.exists():
        data = json.loads(PUBLISHED_LOG.read_text())
        return set(data.get("published_ids", []))
    return set()


def save_published(ids: set):
    PUBLISHED_LOG.write_text(json.dumps({"published_ids": sorted(ids)}, indent=2))


def get_featured_image(post: dict) -> str | None:
    """Obtiene la URL de la imagen destacada del post."""
    media_id = post.get("featured_media")
    if not media_id:
        return None
    try:
        r = requests.get(
            f"https://proyectodelta.eu/wp-json/wp/v2/media/{media_id}",
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("source_url")
    except Exception:
        pass
    return None


# ─── Generación de texto con Claude ───────────────────────────────────────────

def generate_with_claude(title: str, excerpt: str, url: str, category: str, platform: str) -> str:
    """Genera texto optimizado para cada red social usando Claude API."""
    import anthropic

    prompts = {
        "twitter": f"""Eres el community manager de Proyecto Delta, una organización de ciencia marina y economía azul.
Redacta un tweet en español para esta noticia. Máximo 240 caracteres (sin contar la URL).
Usa 2-3 emojis relevantes y 2-3 hashtags relacionados con el mar, ciencia o sostenibilidad.
Termina con la URL: {url}

Título: {title}
Resumen: {excerpt}
Categoría: {category}

Responde SOLO con el tweet, sin comillas ni explicaciones.""",

        "linkedin": f"""Eres el community manager de Proyecto Delta, organización de investigación marina.
Redacta un post profesional en español para LinkedIn sobre esta noticia.
Incluye: gancho inicial, 2-3 párrafos informativos, reflexión o llamada a la acción, hashtags profesionales.
Máximo 700 caracteres. Incluye la URL al final: {url}

Título: {title}
Resumen: {excerpt}
Categoría: {category}

Responde SOLO con el post, sin comillas ni explicaciones.""",

        "facebook": f"""Eres el community manager de Proyecto Delta, organización de ciencia marina.
Redacta un post en español para Facebook sobre esta noticia.
Tono cercano y divulgativo. Incluye emojis, una pregunta al final para generar interacción, y la URL: {url}
Máximo 500 caracteres.

Título: {title}
Resumen: {excerpt}
Categoría: {category}

Responde SOLO con el post, sin comillas ni explicaciones.""",
    }

    prompt = prompts.get(platform, prompts["twitter"])

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def generate_simple(title: str, excerpt: str, url: str, category: str, platform: str) -> str:
    """Genera texto simple sin Claude (fallback)."""
    emoji_map = {
        "Divulgación": "🔬",
        "Observación": "🌊",
        "Noticias":    "📰",
    }
    emoji = emoji_map.get(category, "🐟")

    clean_excerpt = clean_html(excerpt)[:200]

    if platform == "twitter":
        return f"{emoji} {title}\n\n{clean_excerpt}…\n\n🔗 {url}\n\n#ProyectoDelta #CienciaMarina #EconomíaAzul"
    elif platform == "linkedin":
        return f"{emoji} {title}\n\n{clean_excerpt}…\n\nMás información: {url}\n\n#ProyectoDelta #MarOcéano #Sostenibilidad #CienciaMarina"
    else:
        return f"{emoji} {title}\n\n{clean_excerpt}…\n\n👉 {url}\n\n#ProyectoDelta #CienciaMarina"


# ─── Publicadores por red social ──────────────────────────────────────────────

def post_to_twitter(text: str, image_url: str | None = None) -> bool:
    """Publica en Twitter/X usando la API v2."""
    import tweepy

    client = tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_SECRET"],
    )

    try:
        # Si hay imagen, usar API v1.1 para subirla
        media_id = None
        if image_url:
            try:
                auth = tweepy.OAuth1UserHandler(
                    os.environ["TWITTER_API_KEY"],
                    os.environ["TWITTER_API_SECRET"],
                    os.environ["TWITTER_ACCESS_TOKEN"],
                    os.environ["TWITTER_ACCESS_SECRET"],
                )
                api_v1 = tweepy.API(auth)
                img_data = requests.get(image_url, timeout=10).content
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    tmp.write(img_data)
                    tmp_path = tmp.name
                media = api_v1.media_upload(tmp_path)
                media_id = media.media_id
            except Exception as e:
                print(f"⚠️  No se pudo subir imagen a Twitter: {e}")

        response = client.create_tweet(
            text=text[:280],
            media_ids=[media_id] if media_id else None
        )
        print(f"✅ Twitter: https://twitter.com/i/web/status/{response.data['id']}")
        return True
    except Exception as e:
        print(f"❌ Twitter error: {e}")
        return False


def post_to_linkedin(text: str, image_url: str | None = None) -> bool:
    """Publica en LinkedIn usando la API v2."""
    token  = os.environ["LINKEDIN_ACCESS_TOKEN"]
    person = os.environ["LINKEDIN_PERSON_URN"]  # urn:li:person:XXXXXXXX

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    payload = {
        "author": person,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    try:
        r = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=payload,
            timeout=15,
        )
        if r.status_code in (200, 201):
            print(f"✅ LinkedIn: post publicado correctamente")
            return True
        else:
            print(f"❌ LinkedIn error {r.status_code}: {r.text}")
            return False
    except Exception as e:
        print(f"❌ LinkedIn error: {e}")
        return False


def post_to_facebook(text: str, url: str, image_url: str | None = None) -> bool:
    """Publica en una página de Facebook usando Graph API."""
    token   = os.environ["FACEBOOK_PAGE_TOKEN"]
    page_id = os.environ["FACEBOOK_PAGE_ID"]

    try:
        if image_url:
            params = {
                "url": image_url,
                "caption": text,
                "access_token": token,
            }
            r = requests.post(
                f"https://graph.facebook.com/v19.0/{page_id}/photos",
                data=params, timeout=15
            )
        else:
            params = {
                "message": text,
                "link": url,
                "access_token": token,
            }
            r = requests.post(
                f"https://graph.facebook.com/v19.0/{page_id}/feed",
                data=params, timeout=15
            )

        if r.status_code == 200:
            print(f"✅ Facebook: post publicado correctamente")
            return True
        else:
            print(f"❌ Facebook error {r.status_code}: {r.text}")
            return False
    except Exception as e:
        print(f"❌ Facebook error: {e}")
        return False


# ─── Pipeline principal ───────────────────────────────────────────────────────

def fetch_new_posts(published_ids: set) -> list:
    """Obtiene posts de WordPress que no han sido publicados aún."""
    try:
        r = requests.get(
            WP_API_URL,
            params={"per_page": 10, "orderby": "date", "order": "desc",
                    "_fields": "id,title,excerpt,link,date,categories,featured_media"},
            timeout=15,
        )
        posts = r.json()
        new_posts = [p for p in posts if p["id"] not in published_ids]
        print(f"📥 {len(new_posts)} nuevo(s) post(s) encontrado(s)")
        return new_posts
    except Exception as e:
        print(f"❌ Error obteniendo posts: {e}")
        return []


def process_post(post: dict):
    """Procesa y publica un post en todas las redes activas."""
    post_id  = post["id"]
    title    = clean_html(post["title"]["rendered"])
    excerpt  = clean_html(post["excerpt"]["rendered"])
    url      = post["link"]
    cats     = [CATEGORY_NAMES.get(c, "General") for c in post.get("categories", [])]
    category = cats[0] if cats else "General"
    image_url = get_featured_image(post)

    print(f"\n📝 Procesando: [{post_id}] {title}")
    print(f"   🏷️  Categoría: {category} | 🖼️  Imagen: {'Sí' if image_url else 'No'}")

    use_claude = bool(os.environ.get("ANTHROPIC_API_KEY"))
    results = {}

    # ── Twitter ──
    if os.environ.get("TWITTER_API_KEY"):
        text = (generate_with_claude(title, excerpt, url, category, "twitter")
                if use_claude else
                generate_simple(title, excerpt, url, category, "twitter"))
        results["twitter"] = post_to_twitter(text, image_url)

    # ── LinkedIn ──
    if os.environ.get("LINKEDIN_ACCESS_TOKEN"):
        text = (generate_with_claude(title, excerpt, url, category, "linkedin")
                if use_claude else
                generate_simple(title, excerpt, url, category, "linkedin"))
        results["linkedin"] = post_to_linkedin(text, image_url)

    # ── Facebook ──
    if os.environ.get("FACEBOOK_PAGE_TOKEN"):
        text = (generate_with_claude(title, excerpt, url, category, "facebook")
                if use_claude else
                generate_simple(title, excerpt, url, category, "facebook"))
        results["facebook"] = post_to_facebook(text, url, image_url)

    success = any(results.values())
    if success:
        print(f"   ✅ Post {post_id} publicado en: {[k for k,v in results.items() if v]}")
    else:
        print(f"   ⚠️  No se activó ninguna red social (revisa los secrets)")

    return success


def main():
    print("=" * 60)
    print(f"🚀 Social Scheduler - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    published_ids = load_published()
    print(f"📚 Posts ya publicados: {len(published_ids)}")

    new_posts = fetch_new_posts(published_ids)

    if not new_posts:
        print("✨ No hay posts nuevos. Nada que publicar.")
        return

    for post in new_posts:
        success = process_post(post)
        if success:
            published_ids.add(post["id"])

    save_published(published_ids)
    print("\n✅ Proceso completado.")


if __name__ == "__main__":
    main()
