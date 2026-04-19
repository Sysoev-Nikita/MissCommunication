from flask import Flask, jsonify, render_template, request

from .config import AppConfig
from .service import LanguageTutorService


def create_app() -> Flask:
    config = AppConfig.from_env()

    app = Flask(
        __name__,
        static_folder=str(config.static_dir),
        template_folder=str(config.templates_dir),
    )
    app.secret_key = config.secret_key

    tutor_service = LanguageTutorService.from_config(config)

    @app.get("/")
    def serve_index():
        return render_template(
            "index.html",
            language_options=config.language_options,
            level_options=config.level_options,
            ui_text=config.ui_text,
            app_config=config.frontend_config,
        )

    @app.get("/generate_phrase")
    def generate_phrase():
        try:
            phrase_payload = tutor_service.generate_phrase(
                level=request.args.get("level", config.default_level),
                language=request.args.get("language", config.default_language),
                context=(request.args.get("context") or "").strip(),
            )
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        except Exception:
            return jsonify({"error": config.ui_text["phrase_generation_error"]}), 502

        return jsonify(phrase_payload)

    @app.post("/check_translation")
    def check_translation():
        data = request.get_json(silent=True) or {}
        source_phrase = (data.get("source_phrase") or data.get("german_phrase") or "").strip()
        user_translation = (data.get("user_translation") or "").strip()
        language = (data.get("language") or config.default_language).strip().lower()
        phrase_id = (data.get("phrase_id") or "").strip()

        if not source_phrase or not user_translation:
            return jsonify({"error": config.ui_text["invalid_input_error"]}), 400

        try:
            result = tutor_service.check_translation(
                source_phrase=source_phrase,
                user_translation=user_translation,
                language=language,
                phrase_id=phrase_id,
            )
        except Exception:
            return jsonify({"error": config.ui_text["translation_check_error"]}), 502

        return jsonify(result.to_dict())

    @app.post("/study-items")
    def update_study_items():
        data = request.get_json(silent=True) or {}
        action = (data.get("action") or "").strip().lower()

        if action == "add":
            language = (data.get("language") or config.default_language).strip().lower()
            item_type = (data.get("item_type") or "").strip()
            source_text = (data.get("source_text") or "").strip()
            explanation = (data.get("explanation") or "").strip()

            if not language or not item_type or not source_text:
                return jsonify({"error": config.ui_text["invalid_input_error"]}), 400

            study_item = tutor_service.add_study_item(
                language=language,
                item_type=item_type,
                source_text=source_text,
                explanation=explanation,
            )
            return jsonify({"study_item": study_item})

        if action == "remove":
            item_id = (data.get("item_id") or "").strip()
            if not item_id:
                return jsonify({"error": config.ui_text["invalid_input_error"]}), 400

            removed = tutor_service.remove_study_item(item_id)
            if not removed:
                return jsonify({"error": "Study item not found"}), 404
            return jsonify({"removed": True})

        return jsonify({"error": "Unsupported action"}), 400

    return app


app = create_app()
