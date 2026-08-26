---
name: auto-docs-updater
description: >-
  Skill para verificar cambios en el repositorio git y mantener la documentación,
  CHANGELOG.md y DOCUMENTATION.md actualizados automáticamente en cada cambio o commit.
---

# 📚 Auto Docs Updater Skill

Esta habilidad guía al asistente de IA para revisar el estado del repositorio Git, detectar cambios en el código o arquitectura y actualizar automáticamente la documentación del proyecto antes o después de cada modificación importante.

---

## 📋 Protocolo de Ejecución

Cada vez que se agreguen características, refactorice código o se realicen commits a Git, sigue estos pasos:

### Paso 1: Inspeccionar Cambios en Git
Ejecuta los siguientes comandos para evaluar qué archivos fueron modificados o agregados:
```bash
git status
git diff --stat
```

### Paso 2: Actualizar `DOCUMENTATION.md`
Asegúrate de que `DOCUMENTATION.md` refleje:
- **Estructura del Proyecto:** Archivos clave (`app.py`, `tiktok_crossposter.py`, etc.).
- **Variables y Secretos de API:** Lista exacta de llaves necesarias (`TIKTOK_USERNAME`, `INSTAGRAM_*`, `YOUTUBE_*`, `X_*`, `REDDIT_*`).
- **Guía de Configuración:** Diferencia entre **GitHub Actions Secrets** y **Streamlit Cloud Secrets**.
- **Flujos de Trabajo:** Cómo funciona la publicación inmediata, por lotes, y mediante la cola pendiente (`pending_queue.json`).

### Paso 3: Registrar la Actualización en `CHANGELOG.md`
Agrega una nueva entrada en `CHANGELOG.md` con la fecha actual y el formato:
```markdown
## [Versión / Fecha] - YYYY-MM-DD
### ✨ Añadido
- Descripción de nuevas funciones.
### 🛠️ Modificado
- Cambios en componentes o refactorizaciones.
### 🐛 Corregido
- Errores resueltos.
```

### Paso 4: Sincronizar Documentación en Git
Suma la documentación actualizada a las entregas de git:
```bash
git add DOCUMENTATION.md CHANGELOG.md .agents/
```
