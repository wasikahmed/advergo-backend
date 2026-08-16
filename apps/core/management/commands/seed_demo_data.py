from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Category, Fabric, Product
from apps.content.models import (
    Achievement,
    AchievementKind,
    Banner,
    ClientLogo,
    CompanyInfo,
    GalleryCategory,
    GalleryItem,
    HomeSectionBanner,
    HomeSectionKey,
    ProcessStep,
    Stat,
)
from apps.pricing.models import CategoryPriceRule, QuantityDiscountTier
from apps.reviews.models import Review, ReviewStatus

CATEGORIES = [
    {
        "slug": "football",
        "name": "Football",
        "description": "Jersey · Trouser · Shorts",
        "is_featured": True,
    },
    {"slug": "cycling", "name": "Cycling", "description": "Pro Jersey · Bandana"},
    {
        "slug": "cricket",
        "name": "Cricket",
        "description": "Shirt · Trouser · Cap",
        "is_featured": True,
    },
    {"slug": "marathon", "name": "Marathon", "description": "Jersey · Shorts"},
    {
        "slug": "corporate",
        "name": "Corporate",
        "description": "Polo · T-Shirt · Jacket",
        "is_featured": True,
    },
    # Design-collection categories (from the client brief): a continuously
    # growing library of designs customers browse and pick from directly,
    # separate from the sport-kit categories above. Each has real
    # subcategories (own slug/image/page) via SUBCATEGORIES below, not just
    # a filter pill.
    {
        "slug": "polo",
        "name": "Polo",
        "description": "Full Sleeve · Half Sleeve",
        "is_featured": True,
    },
    {"slug": "round-neck", "name": "Round Neck", "description": "Full Sleeve · Half Sleeve"},
    {"slug": "v-neck", "name": "V-Neck", "description": "Full Sleeve · Half Sleeve"},
    {
        "slug": "winter-collection",
        "name": "Winter Collection",
        "description": "Jacket · Tracksuit · Trouser",
        "is_featured": True,
    },
]

# Real subcategories (own slug/name, nested under a parent) shown on each
# design-collection category's page. Sleeve length for the three shirt
# categories, garment type for Winter.
SUBCATEGORIES = {
    "polo": [("polo-full-sleeve", "Full Sleeve"), ("polo-half-sleeve", "Half Sleeve")],
    "round-neck": [
        ("round-neck-full-sleeve", "Full Sleeve"),
        ("round-neck-half-sleeve", "Half Sleeve"),
    ],
    "v-neck": [("v-neck-full-sleeve", "Full Sleeve"), ("v-neck-half-sleeve", "Half Sleeve")],
    "winter-collection": [
        ("winter-jacket", "Jacket"),
        ("winter-tracksuit", "Tracksuit"),
        ("winter-trouser", "Trouser"),
    ],
}

FABRICS = [
    {
        "name": "Pin Mesh Fabric",
        "grade": "China Premium",
        "best_for": "Football · Marathon",
        "description": "Ultra-lightweight open-weave fabric for maximum airflow during high-intensity sport.",
    },
    {
        "name": "Sugar Mesh Fabric",
        "grade": "China Premium",
        "best_for": "Football · Cricket",
        "description": "Soft textured mesh with superior moisture management and colour fastness.",
    },
    {
        "name": "Brush Jacquard Fabric",
        "grade": "China Spandex",
        "best_for": "Cycling · Marathon",
        "description": "Four-way stretch jacquard — aerodynamic fit with a premium textured surface.",
    },
    {
        "name": "Honeycomb Fabric",
        "grade": "China Premium",
        "best_for": "Corporate · Casual",
        "description": "Structured honeycomb weave — durable, breathable, and professional in finish.",
    },
    {
        "name": "Nylon Spandex Fabric",
        "grade": "China Premium",
        "best_for": "Cycling · Swimming",
        "description": "Lightweight nylon blend with elastic recovery — ideal for skin-tight performance kits.",
    },
    {
        "name": "Lurex Box Mesh Fabric",
        "grade": "China Premium",
        "best_for": "Fashion · Corporate",
        "description": "Shimmer-weave mesh combining style with ventilation for fashion-forward activewear.",
    },
]

PRODUCTS = [
    {
        "name": "Tournament Jersey",
        "category": "football",
        "price_range": "৳450–৳650",
        "fabric": "Polyester Dry-Fit",
        "rating": "4.8",
        "review_count": 124,
        "accent_color": "#1d4ed8",
        "is_featured": True,
    },
    {
        "name": "Cricket Playing Shirt",
        "category": "cricket",
        "price_range": "৳550–৳800",
        "fabric": "Premium Cotton Blend",
        "rating": "4.7",
        "review_count": 89,
        "accent_color": "#065f46",
        "is_featured": True,
    },
    {
        "name": "Cycling Pro Jersey",
        "category": "cycling",
        "price_range": "৳600–৳900",
        "fabric": "Lycra Spandex",
        "rating": "4.9",
        "review_count": 56,
        "accent_color": "#eb2127",
        "is_featured": True,
    },
    {
        "name": "Marathon Running Top",
        "category": "marathon",
        "price_range": "৳380–৳520",
        "fabric": "Mesh Dry-Fit",
        "rating": "4.6",
        "review_count": 43,
        "accent_color": "#7c3aed",
        "is_featured": True,
    },
    {
        "name": "Corporate Polo Shirt",
        "category": "corporate",
        "price_range": "৳500–৳750",
        "fabric": "Piqué Cotton",
        "rating": "4.7",
        "review_count": 201,
        "accent_color": "#374151",
        "is_featured": True,
    },
    {
        "name": "Winter Hoodie",
        "category": "corporate",
        "price_range": "৳700–৳1,000",
        "fabric": "Fleece Interlock",
        "rating": "4.8",
        "review_count": 67,
        "accent_color": "#92400e",
        "is_featured": False,
    },
    # Category showcase: no price_range set -- these aren't ready stock, just
    # examples of category work. A blank price_range is what puts a Product
    # in the "Category Showcase" homepage section instead of "Ready Products";
    # still orderable via the same quote flow, just with no price shown.
    {
        "name": "Football Club Kit Example",
        "category": "football",
        "fabric": "Pin Mesh Fabric",
        "accent_color": "#1d4ed8",
        "is_featured": True,
    },
    {
        "name": "Cricket Team Set Example",
        "category": "cricket",
        "fabric": "Sugar Mesh Fabric",
        "accent_color": "#065f46",
        "is_featured": True,
    },
    {
        "name": "Cycling Squad Kit Example",
        "category": "cycling",
        "fabric": "Brush Jacquard Fabric",
        "accent_color": "#eb2127",
        "is_featured": True,
    },
    {
        "name": "Corporate Uniform Example",
        "category": "corporate",
        "fabric": "Honeycomb Fabric",
        "accent_color": "#374151",
        "is_featured": True,
    },
]

STATS = [
    {"value": "90,000", "label": "Pieces / month"},
    {"value": "200+", "label": "Skilled employees"},
    {"value": "$3M", "label": "Yearly turnover"},
    {"value": "6,000", "label": "SFT facility"},
]

ACHIEVEMENTS = [
    {
        "kind": AchievementKind.DOCUMENT,
        "title": "Trade License",
        "year": "2022",
        "issuing_body": "TRAD/DNCC/027440/2022",
    },
    {
        "kind": AchievementKind.DOCUMENT,
        "title": "TIN Certificate",
        "year": "2021",
        "issuing_body": "National Board of Revenue",
    },
    {
        "kind": AchievementKind.DOCUMENT,
        "title": "BIN VAT Certificate",
        "year": "2019",
        "issuing_body": "Customs, Excise & VAT — Dhaka North",
    },
    {
        "kind": AchievementKind.DOCUMENT,
        "title": "Certificate of Inc.",
        "year": "2021",
        "issuing_body": "Registrar of Joint Stock Companies",
    },
]

CLIENTS = [
    {"name": "ONE Bank", "logo_url": "https://logo.clearbit.com/onebank.com.bd"},
    {"name": "Prime Bank", "logo_url": "https://logo.clearbit.com/primebank.com.bd"},
    {"name": "MetLife", "logo_url": "https://logo.clearbit.com/metlife.com"},
    {"name": "Southeast Bank", "logo_url": "https://logo.clearbit.com/southeastbank.com.bd"},
    {"name": "BRAC Bank", "logo_url": "https://logo.clearbit.com/bracbank.com"},
    {
        "name": "Green Delta Insurance",
        "logo_url": "https://logo.clearbit.com/greendeltainsurance.com",
    },
    {"name": "Bangladesh Krishi Bank", "logo_url": "https://logo.clearbit.com/krishibank.org.bd"},
    {"name": "Unilever", "logo_url": "https://logo.clearbit.com/unilever.com"},
    {"name": "PRAN", "logo_url": "https://logo.clearbit.com/pranfoods.com"},
    {"name": "RFL", "logo_url": "https://logo.clearbit.com/rflbd.com"},
    {"name": "Robi", "logo_url": "https://logo.clearbit.com/robi.com.bd"},
    {"name": "bKash", "logo_url": "https://logo.clearbit.com/bkash.com"},
    {"name": "Nagad", "logo_url": "https://logo.clearbit.com/nagad.com.bd"},
    {"name": "Syngenta", "logo_url": "https://logo.clearbit.com/syngenta.com"},
    {"name": "BRAC University", "logo_url": "https://logo.clearbit.com/bracu.ac.bd"},
    {"name": "ULAB", "logo_url": "https://logo.clearbit.com/ulab.edu.bd"},
    {"name": "Walton", "logo_url": "https://logo.clearbit.com/waltonbd.com"},
    {"name": "Orion Pharma", "logo_url": "https://logo.clearbit.com/orionpharma.com"},
    {"name": "bdjobs.com", "logo_url": "https://logo.clearbit.com/bdjobs.com"},
    {"name": "ACI", "logo_url": "https://logo.clearbit.com/aci-bd.com"},
    {"name": "Incepta Pharma", "logo_url": "https://logo.clearbit.com/inceptapharma.com"},
    {"name": "Walton Hi-Tech", "logo_url": "https://logo.clearbit.com/waltonhitech.com"},
    {"name": "SK+F", "logo_url": "https://logo.clearbit.com/skfbd.com"},
    {"name": "LankaBangla", "logo_url": "https://logo.clearbit.com/lankabangla.com"},
    {"name": "CRP Bangladesh", "logo_url": "https://logo.clearbit.com/crp-bangladesh.org"},
    {"name": "Green University", "logo_url": "https://logo.clearbit.com/green.edu.bd"},
    {"name": "WUB", "logo_url": "https://logo.clearbit.com/wub.edu.bd"},
    {"name": "BDCyclists", "logo_url": "https://logo.clearbit.com/bdcyclists.com"},
    {"name": "Run Bangladesh", "logo_url": "https://logo.clearbit.com/runbangladesh.org"},
]

STEPS = [
    {
        "number": "01",
        "title": "Requirement submission",
        "description": "Share your design concepts, quantity, fabric preferences, and specifications with our team.",
        "emoji": "📋",
    },
    {
        "number": "02",
        "title": "Consultation & quotation",
        "description": "Our experts analyse your requirements, provide technical recommendations, and offer a competitive price.",
        "emoji": "💬",
    },
    {
        "number": "03",
        "title": "Sampling",
        "description": "Upon approval, we develop a prototype sample for your review to confirm design and quality.",
        "emoji": "🧵",
    },
    {
        "number": "04",
        "title": "Production",
        "description": "Once sample is approved, our skilled team initiates large-scale manufacturing with strict quality control.",
        "emoji": "⚙️",
    },
    {
        "number": "05",
        "title": "QA & packing",
        "description": "Every garment undergoes final inspection to meet our quality standards before being professionally packed.",
        "emoji": "🔍",
    },
    {
        "number": "06",
        "title": "Delivery",
        "description": "Prompt, secure delivery of your order — for local distribution or international export.",
        "emoji": "🚚",
    },
]

GALLERY_CATEGORIES = [
    {"slug": "factory", "name": "Factory", "icon": "🏭"},
    {"slug": "clients", "name": "Clients", "icon": "🤝"},
]

GALLERY = [
    {"label": "Design section", "category": "factory", "description": "Design & artwork studio"},
    {
        "label": "Printing section",
        "category": "factory",
        "description": "62-inch sublimation printing",
    },
    {"label": "Cutting section", "category": "factory", "description": "Precision fabric cutting"},
    {
        "label": "Sewing section",
        "category": "factory",
        "description": "60–70 industrial sewing machines",
    },
    {"label": "QC section", "category": "factory", "description": "Quality inspection & standards"},
    {
        "label": "Packing section",
        "category": "factory",
        "description": "Professional packing & dispatch",
    },
    {
        "label": "Football kit delivery",
        "category": "clients",
        "description": "Tournament kit — Dhaka Premier FC",
    },
    {
        "label": "Corporate polo delivery",
        "category": "clients",
        "description": "Corporate order — 200 units",
    },
    {
        "label": "Cycling kit showcase",
        "category": "clients",
        "description": "Cycling pro jersey — BCF",
    },
]

REVIEWS = [
    {
        "name": "Rafiqul Islam",
        "organization": "Dhaka Premier FC",
        "rating": 5,
        "text": "Ordered 25 jerseys for our season. Exceptional quality and precise sizing. The custom print came out perfectly.",
    },
    {
        "name": "Tanvir Hossain",
        "organization": "Corporate Solutions Ltd.",
        "rating": 5,
        "text": "Branded polo shirts for our 80-person team. Professional finish, great fabric. Ordering again next quarter.",
    },
    {
        "name": "Sabbir Rahman",
        "organization": "Chittagong Cycling Club",
        "rating": 4,
        "text": "Custom cycling jerseys with our logo. Lycra quality is top-notch. The team absolutely loves them.",
    },
]

COMPANY = {
    "name": "Advergo Sports & Fashion Wear Ltd.",
    "tagline": "Quality with commitment",
    "phone": "+880 1732 687982",
    "email": "info@advergoltd.com",
    "email_alt": "advergo.sportswear@gmail.com",
    "website": "www.advergo.org",
    "head_office": "Flat # B-5, House # 33, Road # 13, Sector # 10, Uttara, Dhaka-1230",
    "factory": "Near Pukurpar Mosjid, Razabari, Kamarpara, Turag, Uttara, Dhaka-1230",
    "founded": "2019",
    "md": "Md. Ashikul Islam",
    "chairman": "Ariful Islam",
}

BANNER = {
    "title": "Built for champions.\nMade your way.",
    "subtitle": (
        "Custom jersey & sportswear manufacturing for football clubs, cricket teams, "
        "cycling squads, and corporates — since 2019."
    ),
    "cta_label": "Explore products",
    "cta_href": "/products",
    "is_active": True,
    "priority": 10,
}

HOME_SECTION_BANNERS = {
    HomeSectionKey.READY_PRODUCTS: {
        "title": "Club & tournament jerseys, ready to order",
        "href": "/products",
        "is_active": True,
    },
    HomeSectionKey.CATEGORY_SHOWCASE: {
        "title": "See what we make, by category",
        "href": "/portfolio",
        "is_active": True,
    },
    HomeSectionKey.DESIGN_COLLECTION: {
        "title": "Browse our design collection",
        "href": "/categories",
        "is_active": True,
    },
}

# Starting-point base prices only -- roughly the low end of each category's
# existing product price ranges above. Not a real pricing policy; adjust these
# (and add per-fabric rules) from the admin once real cost data is available.
CATEGORY_PRICE_RULES = {
    "football": "450.00",
    "cricket": "550.00",
    "cycling": "600.00",
    "marathon": "380.00",
    "corporate": "500.00",
}

QUANTITY_DISCOUNT_TIERS = [
    {"min_quantity": 50, "discount_percent": "5.0"},
    {"min_quantity": 100, "discount_percent": "10.0"},
    {"min_quantity": 250, "discount_percent": "15.0"},
]


class Command(BaseCommand):
    help = "Seeds catalog/content/reviews with the site's real launch copy (images left blank for later upload)."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {}
        for row in CATEGORIES:
            slug = row.pop("slug")
            obj, _ = Category.objects.update_or_create(slug=slug, defaults=row)
            categories[slug] = obj
        self.stdout.write(f"  categories: {len(categories)}")

        subcategory_count = 0
        for parent_slug, children in SUBCATEGORIES.items():
            for order, (slug, name) in enumerate(children):
                Category.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "parent": categories[parent_slug],
                        "name": name,
                        "order": order,
                    },
                )
                subcategory_count += 1
        self.stdout.write(f"  subcategories: {subcategory_count}")

        for row in FABRICS:
            Fabric.objects.update_or_create(name=row["name"], defaults=row)
        self.stdout.write(f"  fabrics: {len(FABRICS)}")

        for row in PRODUCTS:
            row = dict(row)
            category = categories[row.pop("category")]
            Product.objects.update_or_create(
                name=row["name"], defaults={**row, "category": category}
            )
        self.stdout.write(f"  products: {len(PRODUCTS)}")

        for order, row in enumerate(STATS):
            Stat.objects.update_or_create(label=row["label"], defaults={**row, "order": order})
        self.stdout.write(f"  stats: {len(STATS)}")

        for order, row in enumerate(ACHIEVEMENTS):
            Achievement.objects.update_or_create(
                title=row["title"], defaults={**row, "order": order}
            )
        self.stdout.write(f"  achievements: {len(ACHIEVEMENTS)}")

        for order, row in enumerate(CLIENTS):
            ClientLogo.objects.update_or_create(name=row["name"], defaults={**row, "order": order})
        self.stdout.write(f"  client logos: {len(CLIENTS)}")

        for order, row in enumerate(STEPS):
            ProcessStep.objects.update_or_create(
                number=row["number"], defaults={**row, "order": order}
            )
        self.stdout.write(f"  process steps: {len(STEPS)}")

        gallery_categories = {}
        for order, row in enumerate(GALLERY_CATEGORIES):
            slug = row["slug"]
            obj, _ = GalleryCategory.objects.update_or_create(
                slug=slug, defaults={"name": row["name"], "icon": row["icon"], "order": order}
            )
            gallery_categories[slug] = obj
        self.stdout.write(f"  gallery categories: {len(gallery_categories)}")

        for order, row in enumerate(GALLERY):
            defaults = {**row, "order": order, "category": gallery_categories[row["category"]]}
            GalleryItem.objects.update_or_create(label=row["label"], defaults=defaults)
        self.stdout.write(f"  gallery items: {len(GALLERY)}")

        for row in REVIEWS:
            Review.objects.update_or_create(
                name=row["name"], defaults={**row, "status": ReviewStatus.APPROVED}
            )
        self.stdout.write(f"  reviews: {len(REVIEWS)}")

        CompanyInfo.objects.update_or_create(pk=CompanyInfo.SINGLETON_ID, defaults=COMPANY)
        self.stdout.write("  company info: 1")

        # Only one demo banner is seeded -- clear stale rows from earlier runs
        # (e.g. title copy changes) so re-running this command stays idempotent.
        Banner.objects.all().delete()
        Banner.objects.create(**BANNER)
        self.stdout.write("  banner: 1")

        for section, row in HOME_SECTION_BANNERS.items():
            HomeSectionBanner.objects.update_or_create(section=section, defaults=row)
        self.stdout.write(f"  home section banners: {len(HOME_SECTION_BANNERS)}")

        for slug, price in CATEGORY_PRICE_RULES.items():
            CategoryPriceRule.objects.update_or_create(
                category=categories[slug], defaults={"price_per_unit": price}
            )
        self.stdout.write(f"  category price rules: {len(CATEGORY_PRICE_RULES)}")

        for row in QUANTITY_DISCOUNT_TIERS:
            QuantityDiscountTier.objects.update_or_create(
                min_quantity=row["min_quantity"], defaults=row
            )
        self.stdout.write(f"  quantity discount tiers: {len(QUANTITY_DISCOUNT_TIERS)}")

        self.stdout.write(self.style.SUCCESS("Seed complete."))
