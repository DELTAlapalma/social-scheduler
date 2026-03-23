# 📢 Social Scheduler — Proyecto Delta

Automatización de publicaciones en redes sociales a partir de las entradas del blog [proyectodelta.eu](https://proyectodelta.eu).

## ⚙️ ¿Cómo funciona?

1. **Cada 6 horas** (o manualmente), GitHub Actions ejecuta el script
2. Se consulta la API de WordPress de proyectodelta.eu
3. Se detectan entradas **nuevas** (no publicadas antes)
4. Se genera texto **optimizado por IA** (Claude) para cada red social
5. Se publica en las redes configuradas
6. Se guarda el historial para no repetir publicaciones

## 🔑 Secrets necesarios (GitHub → Settings → Secrets)

### Obligatorio (al menos una red social)
| Secret | Descripción |
|--------|-------------|
| `ANTHROPIC_API_KEY` | API Key de Claude (opcional, mejora los textos) |

### Twitter / X
| Secret | Cómo obtenerlo |
|--------|---------------|
| `TWITTER_API_KEY` | [developer.twitter.com](https://developer.twitter.com) |
| `TWITTER_API_SECRET` | Portal de desarrolladores de X |
| `TWITTER_ACCESS_TOKEN` | Portal de desarrolladores de X |
| `TWITTER_ACCESS_SECRET` | Portal de desarrolladores de X |

### LinkedIn
| Secret | Cómo obtenerlo |
|--------|---------------|
| `LINKEDIN_ACCESS_TOKEN` | [linkedin.com/developers](https://www.linkedin.com/developers/) |
| `LINKEDIN_PERSON_URN` | `urn:li:person:XXXXXXXX` (tu ID de LinkedIn) |

### Facebook
| Secret | Cómo obtenerlo |
|--------|---------------|
| `FACEBOOK_PAGE_TOKEN` | [developers.facebook.com](https://developers.facebook.com) |
| `FACEBOOK_PAGE_ID` | ID numérico de tu página de Facebook |

## 🚀 Activación manual

En GitHub → **Actions** → **Social Publisher** → **Run workflow**

Con la opción **"Forzar publicación"** puedes volver a publicar todos los posts aunque ya hayan sido procesados.

## 📁 Estructura

```
social-scheduler/
├── .github/
│   └── workflows/
│       └── social-publisher.yml   # Workflow de GitHub Actions
├── scripts/
│   ├── publisher.py               # Script principal
│   └── requirements.txt           # Dependencias Python
└── published_posts.json           # Historial de posts publicados
```
