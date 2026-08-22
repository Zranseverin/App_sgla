import secrets
import qrcode
from io import BytesIO
from PIL import Image
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.authentication.models import User
from .forms import FactureForm
from .models import Facture


def _user(request):
    return User.objects.select_related("entreprise__plan", "role").filter(pk=request.session.get("utilisateur_id"), statut="actif").first()


def _layout(user):
    e = user.entreprise
    jours = max((e.date_fin_essai - timezone.localdate()).days, 0) if e.date_fin_essai else 0
    return {"user": user, "entreprise": e, "plan": e.plan, "stats": {"jours_restants": jours}, "user_initials": "".join(x[0].upper() for x in user.nom.split()[:2])}


def facture_list(request):
    user = _user(request)
    if not user:
        return redirect("authentication:connexion")
    factures = Facture.objects.filter(entreprise=user.entreprise).select_related("client", "passage")
    q = request.GET.get("q", "").strip()
    if q:
        factures = factures.filter(Q(numero__icontains=q) | Q(client__nom_complet__icontains=q))
    context = _layout(user)
    context.update({"factures": factures, "query": q, "total_facture": factures.aggregate(v=Sum("montant_total"))["v"] or 0, "total_paye": factures.aggregate(v=Sum("montant_paye"))["v"] or 0})
    return render(request, "facture/index.html", context)


def facture_create(request):
    user = _user(request)
    if not user:
        return redirect("authentication:connexion")
    form = FactureForm(request.POST or None, entreprise=user.entreprise, initial={"date_emission": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        facture = form.save(commit=False)
        facture.entreprise = user.entreprise
        facture.numero = f"FAC-{timezone.localdate():%Y%m}-{secrets.token_hex(3).upper()}"
        facture.created_by = user
        if facture.passage:
            facture.montant_ht = facture.passage.montant_total
            facture.montant_paye = facture.passage.montant_paye
        facture.save()
        messages.success(request, f"La facture {facture.numero} a été créée.")
        return redirect("facture:detail", pk=facture.pk)
    context = _layout(user)
    context.update({"form": form})
    return render(request, "facture/form.html", context)


def facture_detail(request, pk):
    user = _user(request)
    if not user:
        return redirect("authentication:connexion")
    facture = get_object_or_404(Facture.objects.select_related("client", "passage__vehicule", "passage__type_lavage"), pk=pk, entreprise=user.entreprise)
    context = _layout(user)
    context["facture"] = facture
    return render(request, "facture/detail.html", context)


def _pdf_escape(value):
    value = str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return value.encode("cp1252", errors="replace")


def _invoice_pdf(facture, entreprise):
    """Generate an 80 mm thermal-style invoice ticket."""
    commands = []
    page_width, page_height = 226, 650
    logo_data = None
    logo_width = logo_height = 0
    if entreprise.logo_url:
        try:
            with entreprise.logo_url.open("rb") as logo_file:
                logo = Image.open(logo_file).convert("RGB")
                logo.thumbnail((120, 28))
                logo_width, logo_height = logo.size
                output = BytesIO()
                logo.save(output, format="JPEG", quality=90)
                logo_data = output.getvalue()
        except (OSError, ValueError):
            logo_data = None

    def text(x, y, size, value, bold=False):
        font = b"F2" if bold else b"F1"
        commands.append(b"BT /" + font + b" " + str(size).encode() + b" Tf " + str(x).encode() + b" " + str(y).encode() + b" Td (" + _pdf_escape(value) + b") Tj ET")

    def centered(y, size, value, bold=False):
        estimated_width = len(str(value)) * size * 0.52
        text(max(8, int((page_width - estimated_width) / 2)), y, size, value, bold)

    def dotted(y):
        commands.append(f"10 {y} m 216 {y} l [2 3] 0 d S [] 0 d".encode())

    devise = entreprise.devise
    if logo_data:
        logo_x = (page_width - logo_width) // 2
        commands.append(f"q {logo_width} 0 0 {logo_height} {logo_x} 618 cm /Im1 Do Q".encode())
        company_y = 606
    else:
        company_y = 620
    centered(company_y, 14, entreprise.raison_sociale.upper(), True)
    centered(company_y - 18, 8, entreprise.email_contact)
    centered(company_y - 32, 8, f"Tel: {entreprise.telephone_contact or '-'}")
    dotted(563)
    centered(540, 15, "FACTURE", True)
    text(12, 515, 8, f"Date: {facture.date_emission:%d/%m/%Y}", True)
    text(12, 500, 8, f"Client: {facture.client.nom_complet}", True)
    text(12, 485, 8, f"Tel: {facture.client.telephone}")
    commands.append(b"10 460 206 25 re S")
    centered(469, 10, facture.numero, True)
    centered(430, 18, f"{facture.montant_total:.0f} {devise}", True)
    text(12, 400, 8, "Prestation:", True)
    text(72, 400, 8, facture.objet)
    text(12, 383, 8, "Paye:", True)
    text(72, 383, 8, f"{facture.montant_paye:.0f} {devise}")
    text(12, 366, 8, "Reste:", True)
    text(72, 366, 8, f"{facture.montant_restant:.0f} {devise}")
    text(12, 349, 8, "Statut:", True)
    text(72, 349, 8, facture.get_statut_display())

    qr = qrcode.QRCode(version=2, box_size=1, border=0)
    qr.add_data(f"FACTURE|{facture.numero}|{facture.montant_total}|{devise}|{facture.client.nom_complet}")
    qr.make(fit=True)
    matrix = qr.get_matrix()
    module = 3
    qr_size = len(matrix) * module
    qr_x, qr_y = (page_width - qr_size) // 2, 185
    for row, values in enumerate(matrix):
        for col, enabled in enumerate(values):
            if enabled:
                commands.append(f"{qr_x + col * module} {qr_y + (len(matrix) - row - 1) * module} {module} {module} re f".encode())
    dotted(165)
    centered(140, 8, "Cette facture atteste la prestation realisee.")
    centered(123, 8, "A conserver comme justificatif de paiement.")
    centered(100, 8, "Merci pour votre confiance, a tres bientot !", True)
    commands.append(b"10 84 m 216 84 l S")
    centered(65, 7, "Document genere par CleanGo")
    stream = b"\n".join(commands)
    content_number = 7 if logo_data else 6
    image_resource = b" /XObject << /Im1 6 0 R >>" if logo_data else b""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] /Resources << /Font << /F1 4 0 R /F2 5 0 R >>".encode() + image_resource + f" >> /Contents {content_number} 0 R >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    if logo_data:
        objects.append(f"<< /Type /XObject /Subtype /Image /Width {logo_width} /Height {logo_height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(logo_data)} >>\nstream\n".encode() + logo_data + b"\nendstream")
    objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf)); pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf); pdf.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets: pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


def facture_pdf(request, pk):
    user = _user(request)
    if not user:
        return redirect("authentication:connexion")
    facture = get_object_or_404(Facture.objects.select_related("client"), pk=pk, entreprise=user.entreprise)
    response = HttpResponse(_invoice_pdf(facture, user.entreprise), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{facture.numero}.pdf"'
    return response
