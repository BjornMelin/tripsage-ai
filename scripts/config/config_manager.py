#!/usr/bin/env python3
"""TripSage Configuration Manager CLI.

A comprehensive tool for managing TripSage configuration across environments.
Provides validation, template generation, secret management, and deployment utilities.
"""

import argparse
import json
import logging
import secrets
import sys
from pathlib import Path
from typing import Any

from tripsage_core.config import Settings, get_settings, validate_configuration


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConfigManager:
    """Configuration management utilities for TripSage."""

    def __init__(self):
        self.settings: Settings | None = None

    def load_settings(self) -> Settings:
        """Load and cache settings."""
        if self.settings is None:
            self.settings = get_settings()
        return self.settings

    def validate(self) -> bool:
        """Validate current configuration."""
        logger.info("🔍 Validating configuration...")

        try:
            if not validate_configuration():
                logger.exception("❌ Configuration validation failed")
                return False

            settings = self.load_settings()
            security_report = settings.get_security_report()

            logger.info("✅ Configuration validation passed")
            logger.info(f"Environment: {settings.environment}")
            logger.info(f"Debug mode: {settings.debug}")
            logger.info(f"Production ready: {security_report['production_ready']}")

            if security_report["warnings"]:
                logger.warning("⚠️ Security warnings:")
                for warning in security_report["warnings"]:
                    logger.warning(f"  - {warning}")

            return True

        except Exception:
            logger.exception("❌ Validation error")
            return False

    def generate_template(
        self, output_file: str, include_secrets: bool = False
    ) -> bool:
        """Generate environment template file."""
        logger.info("📄 Generating configuration template...")

        try:
            settings = self.load_settings()
            template = settings.export_env_template(include_secrets=include_secrets)

            output_path = Path(output_file)
            with output_path.open(encoding="utf-8") as f:
                f.write(template)

            logger.info(f"✅ Template saved to {output_path}")

            if include_secrets:
                logger.warning("⚠️ Template contains actual secrets - handle securely!")

            return True

        except Exception:
            logger.exception("❌ Template generation failed")
            return False

    def generate_secrets(self, count: int = 1, length: int = 32) -> bool:
        """Generate cryptographically secure secrets."""
        logger.info(f"🔐 Generating {count} secure secret(s) (length: {length})...")

        try:
            for i in range(count):
                secret = secrets.token_urlsafe(length)
                logger.info(f"Secret {i + 1}: {secret}")

            logger.info("✅ Secrets generated successfully")
            logger.warning(
                "⚠️ Store these secrets securely and never commit to version control!"
            )

            return True

        except Exception:
            logger.exception("❌ Secret generation failed")
            return False

    def security_report(self, output_format: str = "json") -> bool:
        """Generate comprehensive security report."""
        logger.info("🛡️ Generating security report...")

        try:
            settings = self.load_settings()

            # Get comprehensive security information
            security_report = settings.get_security_report()
            secret_validation = settings.validate_secrets_security()

            report = {
                "configuration": {
                    "environment": settings.environment,
                    "debug_mode": settings.debug,
                    "log_level": settings.log_level,
                },
                "security": security_report,
                "secrets": {
                    "validation": secret_validation,
                    "all_secure": all(secret_validation.values()),
                },
                "recommendations": self._get_security_recommendations(settings),
            }

            if output_format.lower() == "json":
                print(json.dumps(report, indent=2, default=str))
            else:
                self._print_human_readable_report(report)

            return True

        except Exception:
            logger.exception("❌ Security report generation failed")
            return False

    def _get_security_recommendations(self, settings: Settings) -> list[str]:
        """Get security recommendations based on current configuration."""
        recommendations = []

        if settings.environment == "production":
            if settings.debug:
                recommendations.append("Disable debug mode in production")

            if settings.log_level.upper() == "DEBUG":
                recommendations.append("Use INFO or WARNING log level in production")

            secret_validation = settings.validate_secrets_security()
            for field, is_secure in secret_validation.items():
                if not is_secure:
                    recommendations.append(f"Replace weak secret for {field}")

            if "*" in settings.cors_origins:
                recommendations.append("Restrict CORS origins in production")

        else:
            recommendations.append(
                "Ensure proper secrets are configured for production deployment"
            )

        if not settings.redis_url:
            recommendations.append(
                "Configure Redis for improved performance and caching"
            )

        return recommendations

    def _print_human_readable_report(self, report: dict[str, Any]) -> None:
        """Print human-readable security report."""
        config = report["configuration"]
        security = report["security"]
        secrets_info = report["secrets"]
        recommendations = report["recommendations"]

        print("\n" + "=" * 60)
        print("🛡️  TripSage Security Report")
        print("=" * 60)

        print("\n📋 Configuration:")
        print(f"  Environment: {config['environment']}")
        print(f"  Debug Mode: {config['debug_mode']}")
        print(f"  Log Level: {config['log_level']}")

        print("\n🔒 Security Status:")
        print(f"  Production Ready: {'✅' if security['production_ready'] else '❌'}")
        print(f"  All Secrets Secure: {'✅' if secrets_info['all_secure'] else '❌'}")

        if security.get("warnings"):
            print(f"\n⚠️  Warnings ({len(security['warnings'])}):")
            for warning in security["warnings"]:
                print(f"  - {warning}")

        print("\n🔐 Secret Validation:")
        for field, is_secure in secrets_info["validation"].items():
            status = "✅" if is_secure else "❌"
            print(f"  {field}: {status}")

        if recommendations:
            print(f"\n💡 Recommendations ({len(recommendations)}):")
            for rec in recommendations:
                print(f"  - {rec}")

        print("\n" + "=" * 60)

    def check_environment(self, target_env: str) -> bool:
        """Check if configuration is suitable for target environment."""
        logger.info(f"🎯 Checking configuration for {target_env} environment...")

        try:
            settings = self.load_settings()

            if settings.environment != target_env:
                logger.warning(
                    f"⚠️ Current environment ({settings.environment}) != "
                    f"target ({target_env})"
                )

            issues = []

            if target_env == "production":
                if settings.debug:
                    issues.append("Debug mode must be disabled")

                security_report = settings.get_security_report()
                if not security_report["production_ready"]:
                    issues.extend(security_report.get("warnings", []))

            if issues:
                logger.exception(f"❌ Configuration not suitable for {target_env}:")
                for issue in issues:
                    logger.exception(f" - {issue}")
                return False

            logger.info(f"✅ Configuration is suitable for {target_env}")
            return True

        except Exception:
            logger.exception("❌ Environment check failed")
            return False

    def export_config(self, output_file: str, format_type: str = "env") -> bool:
        """Export configuration in various formats."""
        logger.info(
            f"📤 Exporting configuration to {output_file} (format: {format_type})..."
        )

        try:
            settings = self.load_settings()
            output_path = Path(output_file)

            if format_type.lower() == "env":
                content = settings.export_env_template(include_secrets=False)
            elif format_type.lower() == "json":
                config_dict = settings.model_dump(
                    exclude={
                        "secret_key",
                        "database_service_key",
                        "database_jwt_secret",
                        "openai_api_key",
                    }
                )
                content = json.dumps(config_dict, indent=2, default=str)
            else:
                logger.exception("❌ Unsupported format: %s", format_type)
                return False

            with output_path.open(encoding="utf-8") as f:
                f.write(content)

            logger.info("✅ Configuration exported to %s", output_path)
            return True

        except Exception:
            logger.exception("❌ Export failed")
            return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TripSage Configuration Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s validate                              # Validate current configuration
  %(prog)s template .env.template                # Generate environment template
  %(prog)s secrets --count 3                     # Generate 3 secure secrets
  %(prog)s security-report                       # Show security report
  %(prog)s check-env production                  # Check if ready for production
  %(prog)s export config.json --format json     # Export config as JSON
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    subparsers.add_parser("validate", help="Validate configuration")

    # Template command
    template_parser = subparsers.add_parser(
        "template", help="Generate environment template"
    )
    template_parser.add_argument("output", help="Output file path")
    template_parser.add_argument(
        "--include-secrets",
        action="store_true",
        help="Include actual secret values (dangerous!)",
    )

    # Secrets command
    secrets_parser = subparsers.add_parser("secrets", help="Generate secure secrets")
    secrets_parser.add_argument(
        "--count", type=int, default=1, help="Number of secrets to generate"
    )
    secrets_parser.add_argument("--length", type=int, default=32, help="Secret length")

    # Security report command
    security_parser = subparsers.add_parser(
        "security-report", help="Generate security report"
    )
    security_parser.add_argument(
        "--format", choices=["json", "human"], default="human", help="Output format"
    )

    # Check environment command
    check_env_parser = subparsers.add_parser(
        "check-env", help="Check configuration for environment"
    )
    check_env_parser.add_argument(
        "environment",
        choices=["development", "production", "test"],
        help="Target environment",
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export configuration")
    export_parser.add_argument("output", help="Output file path")
    export_parser.add_argument(
        "--format", choices=["env", "json"], default="env", help="Export format"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    manager = ConfigManager()
    success = False

    try:
        if args.command == "validate":
            success = manager.validate()
        elif args.command == "template":
            success = manager.generate_template(args.output, args.include_secrets)
        elif args.command == "secrets":
            success = manager.generate_secrets(args.count, args.length)
        elif args.command == "security-report":
            success = manager.security_report(args.format)
        elif args.command == "check-env":
            success = manager.check_environment(args.environment)
        elif args.command == "export":
            success = manager.export_config(args.output, args.format)
        else:
            logger.exception(f"❌ Unknown command: {args.command}")
            success = False

    except KeyboardInterrupt:
        logger.info("\n⏹️ Operation cancelled by user")
        success = False
    except Exception:
        logger.exception("❌ Unexpected error")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
