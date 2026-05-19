class TotalVfdResponseParser:
    FISCAL_KEYS = ("rctvnum", "verificationLink", "localTime", "localDate", "rctnum", "gc")

    @classmethod
    def extract_fiscal_payload(cls, body):
        if not isinstance(body, dict):
            return None
        if cls._has_fiscal_data(body):
            return body
        nested = body.get("data")
        if isinstance(nested, dict) and cls._has_fiscal_data(nested):
            return nested
        return None

    @classmethod
    def _has_fiscal_data(cls, payload):
        return bool(
            payload.get("verificationLink")
            or payload.get("rctvnum")
            or payload.get("rctvNum")
        )

    @classmethod
    def parse_fiscal_fields(cls, payload):
        if not payload:
            return {}
        local_date = payload.get("localDate") or ""
        local_time = payload.get("localTime") or payload.get("local_time") or ""
        fiscal_datetime = cls._format_fiscal_datetime(local_date, local_time)
        return {
            "totalvfd_rctvnum": payload.get("rctvnum") or payload.get("rctvNum") or "",
            "totalvfd_verification_link": (
                payload.get("verificationLink") or payload.get("verification_link") or ""
            ),
            "totalvfd_local_time": fiscal_datetime,
            "totalvfd_local_date": local_date,
            "totalvfd_rctnum": str(payload.get("rctnum") or ""),
            "totalvfd_gc": str(payload.get("gc") or ""),
            "totalvfd_z_number": str(payload.get("zNumber") or ""),
        }

    @staticmethod
    def _format_fiscal_datetime(local_date, local_time):
        if local_date and local_time:
            return f"{local_date} {local_time}"
        return local_time or local_date or ""

    @classmethod
    def extract_error_message(cls, body, status_code):
        if not isinstance(body, dict):
            return f"API request failed with status {status_code}."
        for key in ("msg", "message", "error", "detail", "errors"):
            value = body.get(key)
            if value:
                return str(value)
        return f"API request failed with status {status_code}."
