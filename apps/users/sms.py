class SMSNotConfiguredError(Exception):
    """Raised until a real SMS provider (e.g. a local BD gateway) is wired up."""


def send_sms_otp(phone: str, code: str) -> None:
    raise SMSNotConfiguredError(
        "SMS delivery isn't configured yet -- phone verification will work once a provider "
        "(e.g. SSL Wireless, Alpha SMS) is wired up in apps.users.sms.send_sms_otp."
    )
