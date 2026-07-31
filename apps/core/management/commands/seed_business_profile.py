"""Real launch content from Advergo Business Profile-2026.pdf (24 pages).

Unlike seed_demo_data.py (which mixes a few real facts with placeholder/fabricated
filler -- guessed client logo URLs, invented reviews, made-up prices), everything
here is sourced directly from the company's own PDF business profile. Re-running
this command is safe (update_or_create throughout); it also removes a small
amount of fabricated content left behind by seed_demo_data.py (see `handle`).
"""

from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Fabric
from apps.content.models import (
    Achievement,
    BankAccount,
    ClientLogo,
    CompanyInfo,
    GalleryItem,
    MobileBankingAgent,
    ProcessStep,
    Stat,
    TeamMember,
)
from apps.reviews.models import Review

ASSETS = Path(__file__).resolve().parent / "business_profile_assets"

COMPANY = {
    "name": "Advergo Sports & Fashion Wear Ltd.",
    "tagline": "Quality with Commitment",
    "phone": "+880 1732 687982",
    "email": "info@advergoltd.com",
    "email_alt": "advergo.sportswear@gmail.com",
    "website": "www.advergo.org",
    "head_office": "Flat # B-5, House # 33, Road # 13, Sector # 10, Uttara, Dhaka-1230",
    "factory": "Near Pukurpar Mosjid, Razabari, Kamarpara, Turag, Uttara, Dhaka-1230",
    "founded": "2019",
    "md": "Md Ashikul Islam",
    "chairman": "Ariful Islam",
    "trade_license_no": "TRAD/DNCC/027440/2022",
    "about": (
        "Founded in 2019 under the visionary leadership of our Managing Director, Md. Ashikul "
        "Islam, Advergo Sports & Fashion Wear Ltd. has rapidly emerged as a reliable name in the "
        "apparel manufacturing industry. Operating from a dedicated 6,000 SFT facility, we blend "
        "modern technology with skilled craftsmanship to produce premium items including Sports "
        "Jerseys, Trousers, Jackets, ID Card Ribbons, and Caps. We are proud to serve both the "
        "local and international markets, catering to diverse client needs with high-quality "
        "manufacturing solutions. With a robust production capacity of 90,000 pieces per month, "
        "we are well-equipped to meet large-scale demands while maintaining stringent quality "
        "standards. Supported by a committed team of 200+ employees and a strong presence "
        "generating a yearly local turnover of USD $3 million, we are focused on sustainable "
        "growth and industry-leading performance."
    ),
    "mission": (
        "To provide high-quality, innovative, and durable sports and fashion apparel that "
        "empowers athletes and organizations to perform at their best. We are committed to "
        "excellence in manufacturing, timely delivery, and building lasting partnerships with "
        "our clients through superior craftsmanship and personalized service."
    ),
    "vision": (
        "To become a leading global name in the sports and fashion apparel industry, recognized "
        "for our innovation, sustainable practices, and unwavering commitment to quality. We aim "
        "to set new benchmarks in textile manufacturing, ensuring that every garment we produce "
        "reflects the spirit of excellence and meets the evolving needs of our local and "
        "international markets."
    ),
}

STATS = [
    {"value": "90,000+", "label": "Pieces produced monthly"},
    {"value": "200+", "label": "Skilled employees"},
    {"value": "6,000", "label": "SFT production facility"},
    {"value": "2,000+", "label": "Pieces produced daily"},
    {"value": "10,000+", "label": "Local & foreign buyers served"},
    {"value": "$3M", "label": "Yearly local turnover (USD)"},
]

# Corrects seed_demo_data's ACHIEVEMENTS rows, which had the license number and
# issuing body swapped into the wrong fields.
ACHIEVEMENTS = [
    {
        "icon": "🏛️",
        "title": "Trade License",
        "year": "2022",
        "issuing_body": "Dhaka North City Corporation — TRAD/DNCC/027440/2022",
    },
    {
        "icon": "📜",
        "title": "TIN Certificate",
        "year": "2021",
        "issuing_body": "National Board of Revenue — 336544192297",
    },
    {
        "icon": "✅",
        "title": "BIN VAT Certificate",
        "year": "2021",
        "issuing_body": "Customs, Excise & VAT — Dhaka North — 002316975-0102",
    },
    {
        "icon": "🏢",
        "title": "Certificate of Incorporation",
        "year": "2021",
        "issuing_body": "Registrar of Joint Stock Companies & Firms — C-175549/2021",
    },
]

FABRICS = [
    {
        "name": "Pin Mesh Fabric",
        "grade": "China Premium",
        "description": "Ultra-lightweight open-weave fabric for maximum airflow during high-intensity sport.",
        "image": "fabrics/pin-mesh-fabric.png",
    },
    {
        "name": "Sugar Mesh Fabric",
        "grade": "China Premium",
        "description": "Soft textured mesh with superior moisture management and colour fastness.",
        "image": "fabrics/sugar-mesh-fabric.png",
    },
    {
        "name": "Brush Jacquard Fabric",
        "grade": "China Spandex",
        "description": "Four-way stretch jacquard — aerodynamic fit with a premium textured surface.",
        "image": "fabrics/brush-jacquard-fabric.png",
    },
    {
        "name": "Leaf Jacquard Fabric",
        "grade": "China Spandex",
        "description": "Leaf-pattern jacquard weave combining stretch performance with a distinctive texture.",
        "image": "fabrics/leaf-jacquard-fabric.png",
    },
    {
        "name": "Honeycomb Fabric",
        "grade": "China Premium",
        "description": "Structured honeycomb weave — durable, breathable, and professional in finish.",
        "image": "fabrics/honeycomb-fabric.png",
    },
    {
        "name": "Birdseye Mesh Fabric",
        "grade": "China Premium",
        "description": "Classic birdseye-weave mesh with fine ventilation holes for breathable everyday wear.",
        "image": "fabrics/birdseye-mesh-fabric.png",
    },
    {
        "name": "Nylon Spandex Fabric",
        "grade": "China Premium",
        "description": "Lightweight nylon blend with elastic recovery — ideal for skin-tight performance kits.",
        "image": "fabrics/nylon-spandex-fabric.png",
    },
    {
        "name": "Lurex Box Mesh Fabric",
        "grade": "China Premium",
        "description": "Shimmer-weave mesh combining style with ventilation for fashion-forward activewear.",
        "image": "fabrics/lurex-box-mesh-fabric.png",
    },
]

STEPS = [
    {
        "number": "01",
        "title": "Requirement Submission",
        "description": "You share your design concepts, quantity, fabric preferences, and specifications with our team.",
        "emoji": "📋",
    },
    {
        "number": "02",
        "title": "Consultation & Quotation",
        "description": "Our experts analyze your requirements, provide technical recommendations if needed, and offer a competitive price quotation.",
        "emoji": "💬",
    },
    {
        "number": "03",
        "title": "Sampling",
        "description": "Upon approval of the quotation, we develop a prototype sample for your review to ensure the design and quality meet your expectations.",
        "emoji": "🧵",
    },
    {
        "number": "04",
        "title": "Production",
        "description": "Once the sample is approved, our skilled production team initiates large-scale manufacturing in our 6,000 SFT facility, maintaining strict quality control.",
        "emoji": "⚙️",
    },
    {
        "number": "05",
        "title": "Quality Assurance & Packing",
        "description": "Every garment undergoes a final inspection to ensure it meets our quality standards before being professionally packed.",
        "emoji": "🔍",
    },
    {
        "number": "06",
        "title": "Delivery",
        "description": "We ensure prompt, secure delivery of your order, whether for local distribution or international export.",
        "emoji": "🚚",
    },
]

GALLERY = [
    {"label": "Design Section", "category": "factory", "description": "Design & artwork studio", "image": "gallery/design-section.png"},
    {"label": "Printing Section", "category": "factory", "description": "62-inch sublimation printing", "image": "gallery/printing-section.png"},
    {"label": "Heat Press Section", "category": "factory", "description": "62-inch and 36-inch heat press finishing", "image": "gallery/heat-press-section.png"},
    {"label": "Cutting Section", "category": "factory", "description": "Precision fabric cutting", "image": "gallery/cutting-section.png"},
    {"label": "Sewing Section", "category": "factory", "description": "60-70 industrial sewing machines", "image": "gallery/sewing-section.png"},
    {"label": "QC Section", "category": "factory", "description": "Quality inspection & standards", "image": "gallery/qc-section.png"},
    {"label": "Iron Section", "category": "factory", "description": "Final pressing & finishing", "image": "gallery/iron-section.png"},
    {"label": "Packing Section", "category": "factory", "description": "Professional packing & dispatch", "image": "gallery/packing-section.png"},
]

TEAM = [
    {
        "name": "Ariful Islam",
        "role": "Chairman",
        "is_leadership": True,
        "photo": "team/ariful-islam-chairman.png",
        "bio": (
            "Since our journey began in 2019, our commitment has always been to lead with "
            "integrity, innovation, and a focus on quality. At Advergo Sports & Fashion Wear "
            "Ltd., we view our clients not just as customers, but as partners in our success. "
            "Over the past years, we have worked tirelessly to set high standards in the apparel "
            "industry, ensuring that our products reflect the dedication and skill of our team. "
            "As we look to the future, our focus remains on sustainable growth, global "
            "excellence, and contributing positively to the industry while maintaining the trust "
            "you have placed in us."
        ),
    },
    {
        "name": "Md Ashikul Islam",
        "role": "Managing Director",
        "is_leadership": True,
        "photo": "team/md-ashikul-islam-managing-director.png",
        "bio": (
            "At Advergo Sports & Fashion Wear Ltd., we believe that every garment tells a story "
            "of precision, comfort, and performance. My vision for this company has always been "
            "to bridge the gap between world-class manufacturing and affordability. With our "
            "dedicated facility and a team of 200+ skilled professionals, we are constantly "
            "pushing boundaries whether it is through adopting new technology or enhancing our "
            "production capacity to meet global demands. We are driven by the passion to deliver "
            "the best, and I invite you to join us as we continue to craft quality apparel that "
            "empowers people around the world."
        ),
    },
    {"name": "Sumon Ahmed", "role": "Merchandiser", "photo": "team/sumon-ahmed-merchandiser.png"},
    {"name": "Ruhul Amin", "role": "Sr. Designer", "photo": "team/ruhul-amin-sr-designer.png"},
    {"name": "Jubaer Al Tawsin", "role": "Sr. Designer", "photo": "team/jubaer-al-tawsin-sr-designer.png"},
    {"name": "Md Shahriar Alam", "role": "Sr. Designer", "photo": "team/md-shahriar-alam-sr-designer.png"},
    {"name": "Fazle Rabbi", "role": "Designer", "photo": "team/fazle-rabbi-designer.png"},
    {"name": "Md Sajed Ali", "role": "Designer", "photo": "team/md-sajed-ali-designer.png"},
    {"name": "Maruf Hossain", "role": "Designer", "photo": "team/maruf-hossain-designer.png"},
    {"name": "Md Didarul Alam", "role": "Accounts & Admin", "photo": "team/md-didarul-alam-accounts-admin.png"},
    {"name": "Muhammad Ullah", "role": "Marketing Executive", "photo": "team/muhammad-ullah-marketing-executive.png"},
    {"name": "Rasel", "role": "Office Assistant", "photo": "team/rasel-office-assistant.png"},
]

BANK_ACCOUNTS = [
    {
        "bank_name": "City Bank PLC",
        "account_name": "Advergo Sports & Fashion Wear Ltd.",
        "account_number": "1263561641001",
        "routing_number": "225260241",
        "branch_name": "Sonargaon Janapath Branch, Uttara, Dhaka",
        "swift_code": "CIBLBDDH",
    },
    {
        "bank_name": "Dutch-Bangla Bank PLC",
        "account_name": "Advergo Sports & Fashion Wear Ltd.",
        "account_number": "2871100004778",
        "routing_number": "090261512",
        "branch_name": "Kamarpara Branch, Turag, Dhaka",
        "swift_code": "DBBLBDDH",
    },
    {
        "bank_name": "United Commercial Bank PLC",
        "account_name": "Advergo Sports & Fashion Wear Ltd.",
        "account_number": "1662112000000118",
        "routing_number": "245261512",
        "branch_name": "Kamarpara Branch, Turag, Dhaka",
        "swift_code": "UCBLBDDH",
    },
]

MOBILE_BANKING = [
    {"provider": "bKash", "agent_number": "01714045528", "label": "Agent"},
    {"provider": "Nagad", "agent_number": "01778738866", "label": "Agent"},
]

# Fabricated by seed_demo_data.py -- invented customers, never real reviews.
FAKE_REVIEW_NAMES = ["Rafiqul Islam", "Tanvir Hossain", "Sabbir Rahman"]


def _attach_image(instance, field_name, relative_path):
    """Attach a seed asset to an image/file field, but only if it's still empty --
    re-running the command shouldn't re-upload (grows storage every time) or
    clobber a photo an admin has since replaced by hand."""
    path = ASSETS / relative_path
    if not path.exists():
        return
    field = getattr(instance, field_name)
    if field and field.name:
        return
    with path.open("rb") as fh:
        field.save(path.name, File(fh), save=True)


class Command(BaseCommand):
    help = "Seeds real content extracted from Advergo Business Profile-2026.pdf, and removes fabricated demo content."

    @transaction.atomic
    def handle(self, *args, **options):
        CompanyInfo.objects.update_or_create(pk=1, defaults=COMPANY)
        self.stdout.write("  company info: 1")

        for order, row in enumerate(STATS):
            Stat.objects.update_or_create(label=row["label"], defaults={**row, "order": order})
        # Drop old demo stats that aren't in the real set.
        Stat.objects.exclude(label__in=[r["label"] for r in STATS]).delete()
        self.stdout.write(f"  stats: {len(STATS)}")

        for order, row in enumerate(ACHIEVEMENTS):
            Achievement.objects.update_or_create(title=row["title"], defaults={**row, "order": order})
        # Drop stale demo titles that don't exactly match (e.g. "Certificate of Inc.").
        Achievement.objects.exclude(title__in=[r["title"] for r in ACHIEVEMENTS]).delete()
        self.stdout.write(f"  achievements: {len(ACHIEVEMENTS)}")

        for order, row in enumerate(FABRICS):
            row = dict(row)
            image_path = row.pop("image", None)
            obj, _ = Fabric.objects.update_or_create(name=row["name"], defaults={**row, "order": order})
            if image_path:
                _attach_image(obj, "image", image_path)
        self.stdout.write(f"  fabrics: {len(FABRICS)}")

        for order, row in enumerate(STEPS):
            ProcessStep.objects.update_or_create(number=row["number"], defaults={**row, "order": order})
        self.stdout.write(f"  process steps: {len(STEPS)}")

        # Full replace, not update_or_create-by-label -- seed_demo_data's demo rows
        # use slightly different label casing ("Design section" vs "Design Section")
        # so they wouldn't match and would linger as stale duplicates. This also
        # drops seed_demo_data's fabricated "clients" category entries (specific
        # fake customer/order captions, e.g. "Dhaka Premier FC").
        GalleryItem.objects.all().delete()
        for order, row in enumerate(GALLERY):
            row = dict(row)
            image_path = row.pop("image", None)
            obj = GalleryItem.objects.create(**row, order=order)
            if image_path:
                _attach_image(obj, "image", image_path)
        self.stdout.write(f"  gallery items: {len(GALLERY)}")

        for order, row in enumerate(TEAM):
            row = dict(row)
            photo_path = row.pop("photo", None)
            obj, _ = TeamMember.objects.update_or_create(name=row["name"], defaults={**row, "order": order})
            if photo_path:
                _attach_image(obj, "photo", photo_path)
        self.stdout.write(f"  team members: {len(TEAM)}")

        for order, row in enumerate(BANK_ACCOUNTS):
            BankAccount.objects.update_or_create(
                account_number=row["account_number"], defaults={**row, "order": order}
            )
        self.stdout.write(f"  bank accounts: {len(BANK_ACCOUNTS)}")

        for order, row in enumerate(MOBILE_BANKING):
            MobileBankingAgent.objects.update_or_create(
                provider=row["provider"], defaults={**row, "order": order}
            )
        self.stdout.write(f"  mobile banking agents: {len(MOBILE_BANKING)}")

        # Replace ALL client logos with the real set -- seed_demo_data.py's guessed
        # Clearbit URLs are fabricated (several are dead links) and not sourced
        # from anything the company gave us.
        clients_dir = ASSETS / "clients"
        client_files = sorted(clients_dir.glob("*.png")) if clients_dir.exists() else []
        real_client_files = [f for f in client_files if not f.stem.startswith("unidentified")]
        if real_client_files:
            ClientLogo.objects.all().delete()
            for order, path in enumerate(real_client_files):
                name = path.stem.replace("-", " ").title()
                obj = ClientLogo.objects.create(name=name, order=order)
                _attach_image(obj, "logo_image", f"clients/{path.name}")
            self.stdout.write(f"  client logos: {len(real_client_files)}")
        else:
            self.stdout.write(
                self.style.WARNING(
                    "  client logos: skipped (business_profile_assets/clients/ has no images yet)"
                )
            )

        # Remove seed_demo_data.py's fabricated customer reviews.
        deleted, _ = Review.objects.filter(name__in=FAKE_REVIEW_NAMES).delete()
        self.stdout.write(f"  removed fabricated reviews: {deleted}")

        self.stdout.write(self.style.SUCCESS("Business profile seed complete."))
