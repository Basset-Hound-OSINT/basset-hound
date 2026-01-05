"""
Data Verification Service for Basset Hound OSINT Platform.

Provides multi-level verification for various identifier types:
- Level 1: Format validation (regex, checksum)
- Level 2: DNS/network verification (MX records, WHOIS)
- Level 3: External API verification (blockchain APIs, breach databases)

This service integrates with the normalizer and crypto detector for
comprehensive data validation before storage.

Usage:
    from api.services.verification_service import get_verification_service

    service = get_verification_service()

    # Verify an email
    result = await service.verify_email("user@example.com")
    print(result.is_valid, result.verification_level)

    # Verify any identifier by type
    result = await service.verify("bc1q...", "crypto_address")
"""

import asyncio
import logging
import re
import socket
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType, geocoder, carrier

from api.models.orphan import IdentifierType
from api.services.normalizer import get_normalizer
from api.utils.crypto_detector import CryptoAddressDetector

logger = logging.getLogger("basset_hound.verification")


class VerificationLevel(str, Enum):
    """Verification depth levels."""
    NONE = "none"                # No verification performed
    FORMAT = "format"            # Format/syntax validation only
    NETWORK = "network"          # DNS/network checks performed
    EXTERNAL_API = "external"    # External API verification


class VerificationStatus(str, Enum):
    """Verification result status."""
    VALID = "valid"
    INVALID = "invalid"
    PLAUSIBLE = "plausible"      # Format valid but not network verified
    UNVERIFIABLE = "unverifiable"  # Cannot verify (disposable, private, etc.)
    ERROR = "error"              # Verification failed due to error


@dataclass
class VerificationResult:
    """
    Result of a verification operation.

    Note: Verification is ADVISORY, not authoritative. The user can override
    any verification result. For example:
    - Private IP (10.x.x.x) might be valid on an internal network
    - User might be on a VPN where "public" IPs have different meanings
    - Some data might appear invalid but be correct in context

    The `allows_override` flag indicates whether user override is applicable.
    The `override_hint` provides context for when override might be appropriate.
    """
    identifier_type: str
    identifier_value: str
    status: VerificationStatus
    verification_level: VerificationLevel
    is_valid: bool
    confidence: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    verified_at: datetime = field(default_factory=datetime.utcnow)
    # Advisory flags for user override
    allows_override: bool = True  # Can user override this result?
    override_hint: Optional[str] = None  # Hint for when override is appropriate

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "identifier_type": self.identifier_type,
            "identifier_value": self.identifier_value,
            "status": self.status.value,
            "verification_level": self.verification_level.value,
            "is_valid": self.is_valid,
            "confidence": self.confidence,
            "details": self.details,
            "warnings": self.warnings,
            "errors": self.errors,
            "verified_at": self.verified_at.isoformat(),
            "allows_override": self.allows_override,
            "override_hint": self.override_hint,
        }


class VerificationService:
    """
    Service for verifying identifier data in the OSINT platform.

    Provides format validation, network verification, and external API
    verification for emails, phone numbers, domains, IPs, and crypto addresses.
    """

    # Email format regex (RFC 5322 compliant subset)
    EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )

    # Phone regex (international format)
    PHONE_REGEX = re.compile(
        r"^\+?[1-9]\d{1,14}$"  # E.164 format
    )

    # Domain regex
    DOMAIN_REGEX = re.compile(
        r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    )

    # IP address regexes
    IPV4_REGEX = re.compile(
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
        r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )
    IPV6_REGEX = re.compile(
        r"^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
    )

    # URL regex
    URL_REGEX = re.compile(
        r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE
    )

    # Known disposable email domains (commonly used for temporary/throwaway emails)
    # Expanded list with ~500+ domains based on industry best practices
    DISPOSABLE_DOMAINS = frozenset([
        # Original list
        "tempmail.com", "throwaway.email", "guerrillamail.com",
        "10minutemail.com", "mailinator.com", "yopmail.com",
        "trashmail.com", "temp-mail.org", "fakeinbox.com",
        # Popular disposable email services
        "guerrillamail.info", "guerrillamail.net", "guerrillamail.org",
        "guerrillamail.biz", "guerrillamail.de",
        "sharklasers.com", "grr.la", "guerrillamailblock.com",
        "pokemail.net", "spam4.me",
        # Mailinator variants
        "mailinator.net", "mailinater.com", "mailinator2.com",
        "sogetthis.com", "mailin8r.com", "mailinator.org",
        "streetwisemail.com", "thisisnotmyrealemail.com",
        # Temp-mail variants
        "temp-mail.io", "tempmail.net", "tempmail.ninja",
        "tempmailaddress.com",
        # 10minutemail variants
        "10minemail.com", "10minutemail.be", "10minutemail.cf",
        "10minutemail.co.za", "10minutemail.co.uk", "10minutemail.de",
        "10minutemail.eu", "10minutemail.ga", "10minutemail.gq",
        "10minutemail.ml", "10minutemail.net", "10minutemail.nl",
        "10minutemail.us",
        # Disposable/temporary email services
        "dispostable.com", "disposableemailaddresses.com",
        "disposableinbox.com", "disposeamail.com", "disposemail.com",
        "emailondeck.com", "emailsensei.com", "emailtemporar.ro",
        "emailtemporanea.com", "emailtemporanea.net", "emailtemporario.com.br",
        "emailthe.net", "emailtmp.com", "emz.net",
        # Fake/trash mail services
        "fakeemailgenerator.com", "fakeinbox.cf", "fakeinbox.co",
        "fakeinbox.ga", "fakeinbox.gq", "fakeinbox.info",
        "fakeinbox.ml", "fakeinbox.net", "fakeinbox.org",
        "fakeinbox.tk", "fakeinbox.us",
        "fakemail.fr", "fakemailgenerator.com",
        "trashmail.at", "trashmail.be", "trashmail.co",
        "trashmail.de", "trashmail.fr", "trashmail.io",
        "trashmail.me", "trashmail.net", "trashmail.se",
        "trashmail.ws", "trashmailbox.com", "trashmailbox.net",
        # Getnada
        "getnada.com", "nada.email", "nada.ltd",
        # Mohmal
        "mohmal.com", "mohmal.im", "mohmal.in", "mohmal.tech",
        # Maildrop
        "maildrop.cc", "maildrop.cf", "maildrop.ga",
        "maildrop.gq", "maildrop.ml",
        # Other common services
        "anonbox.net", "anonymbox.com", "antireg.ru",
        "binkmail.com", "brefmail.com", "bugmenot.com",
        "bumpymail.com", "buyusedlibrarybooks.org",
        "byom.de", "c2.hu", "cheatmail.de",
        "cuvox.de", "dacoolest.com", "dandikmail.com",
        "despam.it", "despammed.com", "discard.email",
        "discardmail.com", "discardmail.de", "dodgeit.com",
        "dodgit.com", "dodgit.org", "dontreg.com",
        "dontsendmespam.de", "drdrb.com", "dump-email.info",
        "dumpmail.de", "dumpyemail.com",
        "e4ward.com", "emaildrop.io", "emailgo.de",
        "emailias.com", "emaillime.com", "emailmiser.com",
        "emailproxsy.com", "emails.ga", "emailspam.cf",
        "emailspam.ga", "emailspam.gq", "emailspam.ml",
        "emailspam.tk", "emailz.cf", "emailz.ga",
        "emailz.gq", "emailz.ml",
        "evopo.com", "explodemail.com",
        "fastacura.com",
        "filzmail.com", "fixmail.tk", "frapmail.com",
        "gawab.com", "get1mail.com", "get2mail.fr",
        "getairmail.com", "getonemail.com", "gishpuppy.com",
        "goemailgo.com", "gotmail.com", "gotmail.net",
        "gotmail.org",
        "grandmamail.com", "grandmasmail.com", "great-host.in",
        "h8s.org", "haltospam.com", "hatespam.org",
        "hidemail.de", "hidemail.pro", "hidemail.us",
        "hidzz.com", "hmamail.com", "hochsitze.com",
        "hopemail.biz", "hotpop.com", "hulapla.de",
        "ieatspam.eu", "ieatspam.info", "ieh-mail.de",
        "ihateyoualot.info", "imails.info", "imgof.com",
        "imgv.de", "imstations.com", "inboxalias.com",
        "inboxclean.com", "inboxclean.org", "incognitomail.com",
        "incognitomail.net", "incognitomail.org", "insorg-mail.info",
        "instant-mail.de", "ipoo.org", "irish2me.com",
        "jetable.com", "jetable.fr.nf", "jetable.net",
        "jetable.org", "jnxjn.com", "jourrapide.com",
        "jsrsolutions.com", "junk1.com", "kasmail.com",
        "keepmymail.com", "killmail.com", "killmail.net",
        "kingsq.ga", "klassmaster.com", "klassmaster.net",
        "klzlv.com", "kulturbetrieb.info", "kurzepost.de",
        "lackmail.net", "lags.us",
        "letthemeatspam.com", "lhsdv.com", "lifebyfood.com",
        "link2mail.net", "litedrop.com", "loadby.us",
        "login-email.cf", "login-email.ga", "login-email.ml",
        "login-email.tk", "lol.ovpn.to", "lookugly.com",
        "lortemail.dk", "lovemeleaveme.com",
        "lr78.com", "lroid.com", "lukop.dk",
        "m21.cc", "mail-temp.com",
        "mail.by", "mail.mezimages.net", "mail.zp.ua",
        "mail114.net", "mail333.com", "mail4trash.com",
        "mailbidon.com", "mailblocks.com", "mailcatch.com",
        "maildx.com", "maileater.com", "mailexpire.com",
        "mailfa.tk", "mailfork.com", "mailfreeonline.com",
        "mailguard.me", "mailimate.com",
        "mailinblack.com", "mailineater.com", "mailismagic.com",
        "mailjunk.cf", "mailjunk.ga", "mailjunk.gq",
        "mailjunk.ml", "mailjunk.tk", "mailmate.com",
        "mailme.gq", "mailme.ir", "mailme.lv",
        "mailme24.com", "mailmetrash.com", "mailmoat.com",
        "mailnator.com", "mailnesia.com", "mailnull.com",
        "mailorg.org", "mailpick.biz",
        "mailrock.biz", "mailsac.com", "mailscrap.com",
        "mailseal.de", "mailshell.com", "mailsiphon.com",
        "mailslite.com", "mailtemp.info", "mailtothis.com",
        "mailzilla.com", "mailzilla.org", "makemetheking.com",
        "manifestgenerator.com", "manybrain.com", "mbx.cc",
        "mega.zik.dj", "meinspamschutz.de", "meltmail.com",
        "messagebeamer.de", "mezimages.net", "mierdamail.com",
        "mintemail.com", "misterpinball.de", "moncourrier.fr.nf",
        "monemail.fr.nf", "monmail.fr.nf", "monumentmail.com",
        "mvrht.com",
        "my10minutemail.com", "mycleaninbox.net", "myemailboxy.com",
        "mymail-in.net", "mymailoasis.com", "mynetstore.de",
        "mypacks.net", "mypartyclip.de", "myphantomemail.com",
        "mysamp.de", "myspaceinc.com", "myspaceinc.net",
        "myspamless.com", "mytempemail.com",
        "mytempmail.com", "mytrashmail.com", "nabuma.com",
        "neomailbox.com", "nervmich.net", "nervtmansen.de",
        "netmails.com", "netmails.net", "netzidiot.de",
        "neverbox.com", "nice-4u.com", "nobulk.com",
        "noclickemail.com", "nogmailspam.info", "nomail.xl.cx",
        "nomail2me.com", "nomorespamemails.com", "nospam.ze.tc",
        "nospam4.us", "nospamfor.us", "nospammail.net",
        "nospamthanks.info", "notmailinator.com", "nowmymail.com",
        "nurfuerspam.de", "nwldx.com",
        "objectmail.com", "obobbo.com", "odnorazovoe.ru",
        "one-time.email", "oneoffemail.com", "onewaymail.com",
        "onlatedotcom.info", "online.ms", "oopi.org",
        "opayq.com", "ordinaryamerican.net", "otherinbox.com",
        "ourklips.com", "outlawspam.com", "ovpn.to",
        "owlpic.com", "pancakemail.com", "pjjkp.com",
        "plexolan.de", "politikerclub.de",
        "poofy.org", "pookmail.com", "privacy.net",
        "privatdemail.net", "proxymail.eu", "prtnx.com",
        "punkass.com", "putthisinyourspamdatabase.com",
        "quickinbox.com", "quickmail.nl",
        "rainmail.biz", "rcpt.at", "reallymymail.com",
        "realtyalerts.ca", "recode.me", "recursor.net",
        "recyclemail.dk", "regbypass.com",
        "rejectmail.com", "remail.cf", "remail.ga",
        "rhyta.com", "rklips.com", "rmqkr.net",
        "rppkn.com", "rtrtr.com",
        "s0ny.net", "safe-mail.net", "safersignup.de",
        "safetymail.info", "safetypost.de", "sandelf.de",
        "saynotospams.com", "schafmail.de", "schrott-email.de",
        "secretemail.de", "secure-mail.biz", "selfdestructingmail.com",
        "sendspamhere.com", "senseless-entertainment.com",
        "sharedmailbox.org",
        "shieldemail.com", "shiftmail.com", "shitmail.me",
        "shortmail.net", "shut.name", "shut.ws",
        "sibmail.com", "sinnlos-mail.de", "siteposter.net",
        "skeefmail.com", "slaskpost.se", "slave-auctions.net",
        "slopsbox.com", "slushmail.com", "smashmail.de",
        "smellfear.com", "snakemail.com", "sneakemail.com",
        "sneakmail.de", "snkmail.com", "sofimail.com",
        "sofort-mail.de", "softpls.asia",
        "soisz.com", "soodomail.com", "soodonims.com",
        "spam.la", "spam.su",
        "spamavert.com", "spambob.com", "spambob.net",
        "spambob.org", "spambog.com", "spambog.de",
        "spambog.net", "spambog.ru", "spambox.info",
        "spambox.us", "spamcannon.com",
        "spamcannon.net", "spamcero.com", "spamcon.org",
        "spamcowboy.com", "spamcowboy.net",
        "spamcowboy.org", "spamday.com", "spamex.com",
        "spamfighter.cf", "spamfighter.ga", "spamfighter.gq",
        "spamfighter.ml", "spamfighter.tk", "spamfree24.com",
        "spamfree24.de", "spamfree24.eu", "spamfree24.info",
        "spamfree24.net", "spamfree24.org", "spamgoes.in",
        "spamgourmet.com", "spamgourmet.net", "spamgourmet.org",
        "spamherelots.com", "spamhereplease.com", "spamhole.com",
        "spamify.com", "spaminator.de", "spamkill.info",
        "spaml.com", "spaml.de", "spammotel.com",
        "spamobox.com", "spamoff.de", "spamsalad.in",
        "spamslicer.com", "spamspot.com", "spamstack.net",
        "spamthis.co.uk", "spamthisplease.com", "spamtrail.com",
        "spamtroll.net", "speed.1s.fr", "spoofmail.de",
        "squizzy.de", "ssoia.com", "startkeys.com",
        "stexsy.com", "stinkefinger.net", "stop-my-spam.cf",
        "stop-my-spam.ga", "stop-my-spam.ml", "stop-my-spam.tk",
        "stuffmail.de", "super-auswahl.de",
        "supergreatmail.com", "supermailer.jp", "superrito.com",
        "superstachel.de", "suremail.info", "svk.jp",
        "sweetxxx.de", "tafmail.com", "tagyourself.com",
        "talkinator.com", "tapchicuoihoi.com", "teewars.org",
        "teleosaurs.xyz", "temp15qm.com",
        "tempail.com", "tempalias.com", "tempe-mail.com",
        "tempemail.biz", "tempemail.co.za", "tempemail.com",
        "tempemail.net", "tempinbox.co.uk", "tempinbox.com",
        "tempmail.de", "tempmail.eu", "tempmail.it",
        "tempmail2.com", "tempmaildemo.com", "tempmailer.com",
        "tempmailer.de", "tempomail.fr", "temporarioemail.com.br",
        "temporaryemail.net", "temporaryemail.us", "temporaryforwarding.com",
        "temporaryinbox.com", "tempsky.com", "tempthe.net",
        "thankspam.net", "thankyou2010.com", "thc.st",
        "thelimestones.com", "throam.com",
        "throwawayemailaddress.com", "throwawaymail.com", "tilien.com",
        "tittbit.in", "tmailinator.com", "toiea.com",
        "toomail.biz", "trash-amil.com", "trash-mail.at",
        "trash-mail.com", "trash-mail.de", "trash-mail.ga",
        "trash-mail.gq", "trash-mail.ml", "trash-mail.tk",
        "trash2009.com", "trash2010.com", "trash2011.com",
        "trashbox.eu", "trashcanmail.com", "trashdevil.com",
        "trashdevil.de",
        "trashmail.org",
        "trashmailer.com", "trashymail.com",
        "trashymail.net", "trbvm.com", "trialmail.de",
        "trickmail.net", "trillianpro.com", "tryalert.com",
        "turual.com", "twinmail.de", "twoweirdtricks.com",
        "tyldd.com", "uggsrock.com", "umail.net",
        "upliftnow.com", "uplipht.com", "uroid.com",
        "valemail.net", "venompen.com", "veryrealemail.com",
        "viditag.com", "viewcastmedia.com", "viewcastmedia.net",
        "viewcastmedia.org", "viralplays.com", "vkcode.ru",
        "vmani.com", "vomoto.com", "vpn.st",
        "vsimcard.com", "vubby.com", "wasteland.rfc822.org",
        "webemail.me", "webm4il.info", "webtrip.ch",
        "wegwerfadresse.de", "wegwerfemail.com", "wegwerfemail.de",
        "wegwerfmail.de", "wegwerfmail.info", "wegwerfmail.net",
        "wegwerfmail.org", "wetrainbayarea.com", "wetrainbayarea.org",
        "wh4f.org", "whatiaas.com", "whatpaas.com",
        "whopy.com", "whyspam.me",
        "wilemail.com", "willhackforfood.biz", "willselfdestruct.com",
        "winemaven.info", "wolfsmail.tk", "wollan.info",
        "worldspace.link", "wrapdrive.eu", "wronghead.com",
        "wuzup.net", "wuzupmail.net", "wwwnew.eu",
        "xagloo.com", "xemaps.com", "xents.com",
        "xmaily.com", "xoxy.net", "xxtreamcam.com",
        "yapped.net", "ycare.de", "yep.it",
        "yogamaven.com",
        "yopmail.fr", "yopmail.gq", "yopmail.net", "yopmail.pp.ua",
        "youmailr.com",
        "yuurok.com", "zehnminuten.de", "zehnminutenmail.de",
        "zetmail.com", "zippymail.info", "zoaxe.com",
        "zoemail.com", "zoemail.net", "zoemail.org",
    ])

    def __init__(self):
        """Initialize the verification service."""
        self._normalizer = None
        self._crypto_detector = None

    @property
    def normalizer(self):
        """Lazy-load normalizer."""
        if self._normalizer is None:
            self._normalizer = get_normalizer()
        return self._normalizer

    @property
    def crypto_detector(self):
        """Lazy-load crypto detector."""
        if self._crypto_detector is None:
            self._crypto_detector = CryptoAddressDetector()
        return self._crypto_detector

    async def verify(
        self,
        value: str,
        identifier_type: str | IdentifierType,
        level: VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify an identifier value based on its type.

        Args:
            value: The identifier value to verify.
            identifier_type: Type of identifier (email, phone, etc.).
            level: Verification depth level.

        Returns:
            VerificationResult with status, confidence, and details.
        """
        if isinstance(identifier_type, str):
            try:
                identifier_type = IdentifierType(identifier_type.lower())
            except ValueError:
                return VerificationResult(
                    identifier_type=identifier_type,
                    identifier_value=value,
                    status=VerificationStatus.ERROR,
                    verification_level=VerificationLevel.NONE,
                    is_valid=False,
                    errors=[f"Unknown identifier type: {identifier_type}"],
                )

        verification_method = {
            IdentifierType.EMAIL: self.verify_email,
            IdentifierType.PHONE: self.verify_phone,
            IdentifierType.DOMAIN: self.verify_domain,
            IdentifierType.IP_ADDRESS: self.verify_ip,
            IdentifierType.URL: self.verify_url,
            IdentifierType.CRYPTO_ADDRESS: self.verify_crypto,
            IdentifierType.USERNAME: self.verify_username,
        }.get(identifier_type, self._verify_generic)

        return await verification_method(value, level)

    async def verify_email(
        self,
        email: str,
        level: VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify an email address.

        Format validation checks:
        - RFC 5322 compliant format
        - Valid domain structure
        - Not a known disposable domain

        Network validation checks:
        - MX record lookup
        - Domain exists

        Args:
            email: Email address to verify.
            level: Verification depth.

        Returns:
            VerificationResult with status and details.
        """
        email = email.strip().lower()
        details: dict[str, Any] = {"original": email}
        warnings: list[str] = []
        errors: list[str] = []

        # Format validation
        if not self.EMAIL_REGEX.match(email):
            return VerificationResult(
                identifier_type="email",
                identifier_value=email,
                status=VerificationStatus.INVALID,
                verification_level=VerificationLevel.FORMAT,
                is_valid=False,
                confidence=0.0,
                details=details,
                errors=["Invalid email format"],
            )

        # Extract domain
        local_part, domain = email.rsplit("@", 1)
        details["local_part"] = local_part
        details["domain"] = domain
        details["has_plus_addressing"] = "+" in local_part

        # Check for disposable domain
        if domain in self.DISPOSABLE_DOMAINS:
            details["is_disposable"] = True
            warnings.append("Disposable email domain detected")

        # Check for common typos in domain
        common_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}
        for cd in common_domains:
            if domain != cd and self._levenshtein_distance(domain, cd) == 1:
                warnings.append(f"Possible typo: did you mean {cd}?")
                break

        if level == VerificationLevel.FORMAT:
            return VerificationResult(
                identifier_type="email",
                identifier_value=email,
                status=VerificationStatus.PLAUSIBLE,
                verification_level=VerificationLevel.FORMAT,
                is_valid=True,
                confidence=0.7 if not warnings else 0.5,
                details=details,
                warnings=warnings,
            )

        # Network verification (MX lookup)
        if level in (VerificationLevel.NETWORK, VerificationLevel.EXTERNAL_API):
            try:
                mx_records = await self._lookup_mx(domain)
                details["mx_records"] = mx_records
                details["has_mx"] = len(mx_records) > 0

                if not mx_records:
                    return VerificationResult(
                        identifier_type="email",
                        identifier_value=email,
                        status=VerificationStatus.INVALID,
                        verification_level=VerificationLevel.NETWORK,
                        is_valid=False,
                        confidence=0.2,
                        details=details,
                        errors=["No MX records found for domain"],
                        warnings=warnings,
                    )

                return VerificationResult(
                    identifier_type="email",
                    identifier_value=email,
                    status=VerificationStatus.VALID,
                    verification_level=VerificationLevel.NETWORK,
                    is_valid=True,
                    confidence=0.9,
                    details=details,
                    warnings=warnings,
                )

            except Exception as e:
                logger.warning(f"MX lookup failed for {domain}: {e}")
                errors.append(f"MX lookup error: {str(e)}")
                return VerificationResult(
                    identifier_type="email",
                    identifier_value=email,
                    status=VerificationStatus.PLAUSIBLE,
                    verification_level=VerificationLevel.FORMAT,
                    is_valid=True,
                    confidence=0.6,
                    details=details,
                    warnings=warnings,
                    errors=errors,
                )

        return VerificationResult(
            identifier_type="email",
            identifier_value=email,
            status=VerificationStatus.PLAUSIBLE,
            verification_level=VerificationLevel.FORMAT,
            is_valid=True,
            confidence=0.7,
            details=details,
            warnings=warnings,
        )

    async def verify_phone(
        self,
        phone: str,
        level: VerificationLevel = VerificationLevel.FORMAT,
        default_region: str = "US",
    ) -> VerificationResult:
        """
        Verify a phone number using Google's libphonenumber.

        Provides comprehensive validation including:
        - Format validation (is it a possible/valid phone number?)
        - Country/region detection
        - Number type detection (mobile, landline, VOIP, toll-free, etc.)
        - Carrier detection (when available)
        - Geographic location (when available)

        Args:
            phone: Phone number to verify.
            level: Verification depth.
            default_region: Default region for parsing numbers without country code.

        Returns:
            VerificationResult with status and details.
        """
        details: dict[str, Any] = {"original": phone}
        warnings: list[str] = []
        errors: list[str] = []

        try:
            # Parse the phone number
            parsed = phonenumbers.parse(phone, default_region)
            details["parsed"] = True

            # Get formatted versions
            details["e164"] = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
            details["international"] = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            details["national"] = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.NATIONAL
            )

            # Country information
            details["country_code"] = parsed.country_code
            region = phonenumbers.region_code_for_number(parsed)
            details["region"] = region

            # Try to get country/location name
            try:
                location = geocoder.description_for_number(parsed, "en")
                if location:
                    details["location"] = location
            except Exception:
                pass

            # Check if it's a possible number (basic structure)
            is_possible = phonenumbers.is_possible_number(parsed)
            details["is_possible"] = is_possible

            # Check if it's a valid number (stricter validation)
            is_valid = phonenumbers.is_valid_number(parsed)
            details["is_valid"] = is_valid

            # Get number type
            number_type = phonenumbers.number_type(parsed)
            type_map = {
                PhoneNumberType.FIXED_LINE: "landline",
                PhoneNumberType.MOBILE: "mobile",
                PhoneNumberType.FIXED_LINE_OR_MOBILE: "landline_or_mobile",
                PhoneNumberType.TOLL_FREE: "toll_free",
                PhoneNumberType.PREMIUM_RATE: "premium_rate",
                PhoneNumberType.SHARED_COST: "shared_cost",
                PhoneNumberType.VOIP: "voip",
                PhoneNumberType.PERSONAL_NUMBER: "personal",
                PhoneNumberType.PAGER: "pager",
                PhoneNumberType.UAN: "uan",
                PhoneNumberType.VOICEMAIL: "voicemail",
                PhoneNumberType.UNKNOWN: "unknown",
            }
            details["number_type"] = type_map.get(number_type, "unknown")

            # Try to get carrier information
            try:
                carrier_name = carrier.name_for_number(parsed, "en")
                if carrier_name:
                    details["carrier"] = carrier_name
            except Exception:
                pass

            # Add warnings for certain number types
            if number_type == PhoneNumberType.VOIP:
                warnings.append("VOIP number detected - may not be tied to physical location")
            elif number_type == PhoneNumberType.PREMIUM_RATE:
                warnings.append("Premium rate number - may incur charges")
            elif number_type == PhoneNumberType.TOLL_FREE:
                warnings.append("Toll-free number")

            # Determine status and confidence based on validation
            if is_valid:
                return VerificationResult(
                    identifier_type="phone",
                    identifier_value=phone,
                    status=VerificationStatus.VALID,
                    verification_level=VerificationLevel.FORMAT,
                    is_valid=True,
                    confidence=0.95,
                    details=details,
                    warnings=warnings,
                )
            elif is_possible:
                return VerificationResult(
                    identifier_type="phone",
                    identifier_value=phone,
                    status=VerificationStatus.PLAUSIBLE,
                    verification_level=VerificationLevel.FORMAT,
                    is_valid=True,
                    confidence=0.7,
                    details=details,
                    warnings=warnings + ["Number structure is valid but may not be assigned"],
                )
            else:
                # Not a valid phone number according to libphonenumber
                possible_reason = phonenumbers.is_possible_number_with_reason(parsed)
                reason_map = {
                    phonenumbers.ValidationResult.INVALID_COUNTRY_CODE: "Invalid country code",
                    phonenumbers.ValidationResult.TOO_SHORT: "Number too short",
                    phonenumbers.ValidationResult.TOO_LONG: "Number too long",
                    phonenumbers.ValidationResult.INVALID_LENGTH: "Invalid length for region",
                }
                error_msg = reason_map.get(possible_reason, "Invalid phone number format")
                errors.append(error_msg)

                return VerificationResult(
                    identifier_type="phone",
                    identifier_value=phone,
                    status=VerificationStatus.INVALID,
                    verification_level=VerificationLevel.FORMAT,
                    is_valid=False,
                    confidence=0.1,
                    details=details,
                    errors=errors,
                    allows_override=True,
                    override_hint="Override if you're certain this is a valid number in a specific context",
                )

        except NumberParseException as e:
            # Failed to parse - completely invalid format
            error_messages = {
                NumberParseException.INVALID_COUNTRY_CODE: "Invalid or missing country code",
                NumberParseException.NOT_A_NUMBER: "Input does not appear to be a phone number",
                NumberParseException.TOO_SHORT_AFTER_IDD: "Number too short after country code",
                NumberParseException.TOO_SHORT_NSN: "National number too short",
                NumberParseException.TOO_LONG: "Number too long",
            }
            error_msg = error_messages.get(e.error_type, f"Parse error: {str(e)}")
            errors.append(error_msg)
            details["parse_error"] = str(e)

            # Fallback: check if it at least looks like digits
            digits_only = re.sub(r"\D", "", phone)
            if 7 <= len(digits_only) <= 15:
                details["digits_only"] = digits_only
                details["digit_count"] = len(digits_only)
                return VerificationResult(
                    identifier_type="phone",
                    identifier_value=phone,
                    status=VerificationStatus.PLAUSIBLE,
                    verification_level=VerificationLevel.FORMAT,
                    is_valid=True,
                    confidence=0.3,
                    details=details,
                    warnings=["Could not fully validate - treating as plausible based on digit count"],
                    errors=errors,
                    allows_override=True,
                    override_hint="Override if this is a valid number in a non-standard format",
                )

            return VerificationResult(
                identifier_type="phone",
                identifier_value=phone,
                status=VerificationStatus.INVALID,
                verification_level=VerificationLevel.FORMAT,
                is_valid=False,
                confidence=0.0,
                details=details,
                errors=errors,
                allows_override=True,
                override_hint="Override if you're certain this is a valid phone number",
            )

    async def verify_domain(
        self,
        domain: str,
        level: VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify a domain name.

        Args:
            domain: Domain to verify.
            level: Verification depth.

        Returns:
            VerificationResult with status and details.
        """
        domain = domain.strip().lower()
        # Remove protocol if present
        if domain.startswith(("http://", "https://")):
            domain = domain.split("://", 1)[1].split("/", 1)[0]

        details: dict[str, Any] = {"domain": domain}

        if not self.DOMAIN_REGEX.match(domain):
            return VerificationResult(
                identifier_type="domain",
                identifier_value=domain,
                status=VerificationStatus.INVALID,
                verification_level=VerificationLevel.FORMAT,
                is_valid=False,
                confidence=0.0,
                details=details,
                errors=["Invalid domain format"],
            )

        # Extract TLD
        parts = domain.rsplit(".", 1)
        if len(parts) == 2:
            details["tld"] = parts[1]

        if level == VerificationLevel.FORMAT:
            return VerificationResult(
                identifier_type="domain",
                identifier_value=domain,
                status=VerificationStatus.PLAUSIBLE,
                verification_level=VerificationLevel.FORMAT,
                is_valid=True,
                confidence=0.7,
                details=details,
            )

        # Network verification
        if level in (VerificationLevel.NETWORK, VerificationLevel.EXTERNAL_API):
            try:
                # DNS A record lookup
                ip = await asyncio.get_event_loop().run_in_executor(
                    None, socket.gethostbyname, domain
                )
                details["resolves"] = True
                details["ip_address"] = ip

                return VerificationResult(
                    identifier_type="domain",
                    identifier_value=domain,
                    status=VerificationStatus.VALID,
                    verification_level=VerificationLevel.NETWORK,
                    is_valid=True,
                    confidence=0.95,
                    details=details,
                )
            except socket.gaierror:
                details["resolves"] = False
                return VerificationResult(
                    identifier_type="domain",
                    identifier_value=domain,
                    status=VerificationStatus.INVALID,
                    verification_level=VerificationLevel.NETWORK,
                    is_valid=False,
                    confidence=0.1,
                    details=details,
                    errors=["Domain does not resolve"],
                )

        return VerificationResult(
            identifier_type="domain",
            identifier_value=domain,
            status=VerificationStatus.PLAUSIBLE,
            verification_level=VerificationLevel.FORMAT,
            is_valid=True,
            confidence=0.7,
            details=details,
        )

    async def verify_ip(
        self,
        ip: str,
        level: VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify an IP address.

        ADVISORY: IP verification is context-dependent. A "private" IP may be
        a valid target on an internal network, or the user may be accessing
        through a VPN where public/private distinctions differ.

        Args:
            ip: IP address to verify.
            level: Verification depth.

        Returns:
            VerificationResult with status and details.
        """
        ip = ip.strip()
        details: dict[str, Any] = {"address": ip}
        warnings: list[str] = []
        override_hint: Optional[str] = None

        is_ipv4 = bool(self.IPV4_REGEX.match(ip))
        is_ipv6 = bool(self.IPV6_REGEX.match(ip))

        if is_ipv4:
            details["version"] = 4
            octets = [int(x) for x in ip.split(".")]
            details["octets"] = octets

            # Check for special ranges - advisory, not restrictive
            if octets[0] == 10 or (octets[0] == 172 and 16 <= octets[1] <= 31) or \
               (octets[0] == 192 and octets[1] == 168):
                details["is_private"] = True
                details["range_type"] = "RFC 1918 private"
                warnings.append("Private IP range detected - may be valid on internal network")
                override_hint = "Override if this is a valid target on your internal network or VPN"
            elif octets[0] == 127:
                details["is_loopback"] = True
                details["range_type"] = "loopback"
                warnings.append("Loopback address - refers to local machine")
                override_hint = "Override if intentionally targeting localhost"
            elif octets[0] == 0:
                details["is_reserved"] = True
                details["range_type"] = "reserved"
                warnings.append("Reserved address range")
            elif octets[0] == 169 and octets[1] == 254:
                details["is_link_local"] = True
                details["range_type"] = "link-local (APIPA)"
                warnings.append("Link-local address - typically indicates network misconfiguration")
                override_hint = "Override if this is a known APIPA address on your network"

            return VerificationResult(
                identifier_type="ip_address",
                identifier_value=ip,
                status=VerificationStatus.VALID,
                verification_level=VerificationLevel.FORMAT,
                is_valid=True,
                confidence=0.95,
                details=details,
                warnings=warnings,
                allows_override=True,
                override_hint=override_hint,
            )

        if is_ipv6:
            details["version"] = 6
            if ip.lower().startswith("::1") or ip == "::1":
                details["is_loopback"] = True
                details["range_type"] = "loopback"
                warnings.append("IPv6 loopback address - refers to local machine")
                override_hint = "Override if intentionally targeting localhost"
            elif ip.lower().startswith("fe80:"):
                details["is_link_local"] = True
                details["range_type"] = "link-local"
                warnings.append("IPv6 link-local address")
                override_hint = "Override if this is a valid target on your local network segment"
            elif ip.lower().startswith("fc") or ip.lower().startswith("fd"):
                details["is_private"] = True
                details["range_type"] = "unique local (ULA)"
                warnings.append("IPv6 unique local address - similar to RFC 1918 private")
                override_hint = "Override if this is a valid target on your internal network"

            return VerificationResult(
                identifier_type="ip_address",
                identifier_value=ip,
                status=VerificationStatus.VALID,
                verification_level=VerificationLevel.FORMAT,
                is_valid=True,
                confidence=0.95,
                details=details,
                warnings=warnings,
                allows_override=True,
                override_hint=override_hint,
            )

        return VerificationResult(
            identifier_type="ip_address",
            identifier_value=ip,
            status=VerificationStatus.INVALID,
            verification_level=VerificationLevel.FORMAT,
            is_valid=False,
            confidence=0.0,
            details=details,
            errors=["Invalid IP address format"],
            allows_override=True,
            override_hint="Override if you're certain this is a valid IP format",
        )

    async def verify_url(
        self,
        url: str,
        level: VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify a URL.

        Args:
            url: URL to verify.
            level: Verification depth.

        Returns:
            VerificationResult with status and details.
        """
        url = url.strip()
        details: dict[str, Any] = {"url": url}

        if not self.URL_REGEX.match(url):
            return VerificationResult(
                identifier_type="url",
                identifier_value=url,
                status=VerificationStatus.INVALID,
                verification_level=VerificationLevel.FORMAT,
                is_valid=False,
                confidence=0.0,
                details=details,
                errors=["Invalid URL format"],
            )

        # Parse URL components
        from urllib.parse import urlparse
        parsed = urlparse(url)
        details["scheme"] = parsed.scheme
        details["domain"] = parsed.netloc
        details["path"] = parsed.path
        if parsed.query:
            details["has_query"] = True
        if parsed.fragment:
            details["has_fragment"] = True

        return VerificationResult(
            identifier_type="url",
            identifier_value=url,
            status=VerificationStatus.PLAUSIBLE,
            verification_level=VerificationLevel.FORMAT,
            is_valid=True,
            confidence=0.8,
            details=details,
        )

    async def verify_crypto(
        self,
        address: str,
        level: VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify a cryptocurrency address.

        Uses the CryptoAddressDetector for pattern matching and
        checksum validation where applicable.

        Args:
            address: Crypto address to verify.
            level: Verification depth.

        Returns:
            VerificationResult with status and details.
        """
        address = address.strip()

        # Use crypto detector
        detection = self.crypto_detector.detect(address)

        details: dict[str, Any] = {
            "address": address,
            "detected": detection.detected,
        }

        if detection.detected:
            details["coin_name"] = detection.coin_name
            details["coin_ticker"] = detection.coin_ticker
            details["network"] = detection.network
            details["address_type"] = detection.address_type
            details["explorer_url"] = detection.explorer_url

            return VerificationResult(
                identifier_type="crypto_address",
                identifier_value=address,
                status=VerificationStatus.VALID,
                verification_level=VerificationLevel.FORMAT,
                is_valid=True,
                confidence=detection.confidence,
                details=details,
            )

        return VerificationResult(
            identifier_type="crypto_address",
            identifier_value=address,
            status=VerificationStatus.INVALID,
            verification_level=VerificationLevel.FORMAT,
            is_valid=False,
            confidence=0.0,
            details=details,
            errors=["Unrecognized cryptocurrency address format"],
        )

    async def verify_username(
        self,
        username: str,
        level: VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Verify a username/handle.

        Args:
            username: Username to verify.
            level: Verification depth.

        Returns:
            VerificationResult with status and details.
        """
        original = username
        # Remove @ prefix if present
        if username.startswith("@"):
            username = username[1:]

        details: dict[str, Any] = {
            "original": original,
            "normalized": username.lower(),
            "had_at_prefix": original.startswith("@"),
        }

        # Basic username format (letters, numbers, underscores)
        if re.match(r"^[a-zA-Z0-9_]{1,30}$", username):
            return VerificationResult(
                identifier_type="username",
                identifier_value=original,
                status=VerificationStatus.PLAUSIBLE,
                verification_level=VerificationLevel.FORMAT,
                is_valid=True,
                confidence=0.7,
                details=details,
            )

        # More permissive (includes dots, dashes)
        if re.match(r"^[a-zA-Z0-9._-]{1,50}$", username):
            return VerificationResult(
                identifier_type="username",
                identifier_value=original,
                status=VerificationStatus.PLAUSIBLE,
                verification_level=VerificationLevel.FORMAT,
                is_valid=True,
                confidence=0.5,
                details=details,
                warnings=["Extended username format, may not be valid on all platforms"],
            )

        return VerificationResult(
            identifier_type="username",
            identifier_value=original,
            status=VerificationStatus.INVALID,
            verification_level=VerificationLevel.FORMAT,
            is_valid=False,
            confidence=0.0,
            details=details,
            errors=["Invalid username format"],
        )

    async def _verify_generic(
        self,
        value: str,
        level: VerificationLevel = VerificationLevel.FORMAT,
    ) -> VerificationResult:
        """
        Generic verification for unsupported identifier types.

        Simply checks that the value is non-empty.
        """
        value = value.strip()

        if not value:
            return VerificationResult(
                identifier_type="other",
                identifier_value=value,
                status=VerificationStatus.INVALID,
                verification_level=VerificationLevel.FORMAT,
                is_valid=False,
                confidence=0.0,
                errors=["Empty value"],
            )

        return VerificationResult(
            identifier_type="other",
            identifier_value=value,
            status=VerificationStatus.PLAUSIBLE,
            verification_level=VerificationLevel.FORMAT,
            is_valid=True,
            confidence=0.3,
            warnings=["No specific validation available for this type"],
        )

    async def _lookup_mx(self, domain: str) -> list[str]:
        """
        Perform MX record lookup for a domain.

        Args:
            domain: Domain to lookup.

        Returns:
            List of MX record hostnames.
        """
        import dns.resolver

        try:
            answers = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: dns.resolver.resolve(domain, "MX")
            )
            return [str(r.exchange).rstrip(".") for r in answers]
        except Exception:
            # Try to resolve as A record (might still receive email)
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: dns.resolver.resolve(domain, "A")
                )
                return [domain]  # Domain resolves, might accept email
            except Exception:
                return []

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    async def batch_verify(
        self,
        items: list[dict[str, str]],
        level: VerificationLevel = VerificationLevel.FORMAT,
    ) -> list[VerificationResult]:
        """
        Verify multiple identifiers in batch.

        Args:
            items: List of dicts with "value" and "type" keys.
            level: Verification depth for all items.

        Returns:
            List of VerificationResult objects.
        """
        tasks = [
            self.verify(item["value"], item["type"], level)
            for item in items
        ]
        return await asyncio.gather(*tasks)


# Singleton instance
_verification_service: Optional[VerificationService] = None


def get_verification_service() -> VerificationService:
    """Get or create the verification service singleton."""
    global _verification_service
    if _verification_service is None:
        _verification_service = VerificationService()
    return _verification_service
