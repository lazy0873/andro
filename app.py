from flask import Flask, request, jsonify, render_template_string
import random
import datetime
from faker import Faker
import re
import json
import requests

app = Flask(__name__)

# BIN info simplificada para validar y tipo tarjeta
BIN_DATABASE = {
    # BIN : { 'brand': 'Visa', 'length': 16 }
    "453957": {'brand': 'Visa', 'length': 16},
    "455673": {'brand': 'Visa', 'length': 16},
    "601100": {'brand': 'Discover', 'length': 16},
    "371449": {'brand': 'Amex', 'length': 15},
    "510510": {'brand': 'MasterCard', 'length': 16},
    # agregar más según se desee
}

def luhn_checksum(card_number):
    digits = [int(d) for d in str(card_number)]
    odd = digits[-1::-2]
    even = digits[-2::-2]
    total = sum(odd)
    for d in even:
        total += sum([int(x) for x in str(d * 2)])
    return total % 10

def generate_luhn(bin_prefix, length):
    number = bin_prefix + ''.join(str(random.randint(0,9)) for _ in range(length - len(bin_prefix) - 1))
    checksum = luhn_checksum(number + '0')
    return number + str((10 - checksum) % 10)

def random_expiry():
    now = datetime.datetime.now()
    return f"{random.randint(1,12):02d}/{str(random.randint(now.year+1, now.year+6))[-2:]}"

def random_cvv(length=3):
    return ''.join(str(random.randint(0,9)) for _ in range(length))

def generate_fake_iban():
    # Simple fake IBAN (not valid) - pattern: CountryCode + 2 digits + 14 alphanumeric
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    digits = '0123456789'
    country_code = random.choice(['DE','FR','ES','IT','NL','BE','CH','GB','PT'])
    check_digits = f"{random.randint(10,99)}"
    bban = ''.join(random.choice(digits + letters) for _ in range(14))
    return country_code + check_digits + bban

def generate_fake_license():
    # Simple fake license plate - 3 letters + 4 digits
    letters = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(3))
    digits = ''.join(str(random.randint(0,9)) for _ in range(4))
    return letters + digits

def get_user_photo():
    try:
        response = requests.get("https://randomuser.me/api/?inc=picture&noinfo")
        if response.ok:
            data = response.json()
            return data['results'][0]['picture']['large']
    except:
        pass
    return ""

# Faker locales extendidos
FAKER_LOCALES = {
    "": "Aleatorio/Default",
    "en_US": "Estados Unidos",
    "es_ES": "España",
    "fr_FR": "Francia",
    "de_DE": "Alemania",
    "it_IT": "Italia",
    "pt_PT": "Portugal",
    "ru_RU": "Rusia",
    "ja_JP": "Japón",
    "zh_CN": "China",
    "ar_SA": "Arabia Saudita",
    "hi_IN": "India",
    "ko_KR": "Corea del Sur",
    # Agregar más si se desea
}

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template_string(TEMPLATE, locales=FAKER_LOCALES)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    bin_input = data.get('bin', '')
    count = int(data.get('count', 1))
    use_custom_date = data.get('custom_date_checkbox', False)
    custom_date = data.get('custom_date', '')
    use_custom_cvv = data.get('custom_cvv_checkbox', False)
    custom_cvv = data.get('custom_cvv', '')
    country = data.get('country', '')
    types_requested = data.get('card_types', [])  # Example extension (Visa, MC, Amex)

    fake = Faker(locale=country) if country else Faker()

    bins = [b.strip() for b in bin_input.split(',') if b.strip()]
    result_cards = []
    result_profiles = []

    def get_bin_info(b):
        for key in BIN_DATABASE:
            if b.startswith(key):
                return BIN_DATABASE[key]
        return None

    # Validación básica y selección de bin y length
    for b in bins:
        if not re.fullmatch(r'\d{6,15}', b):
            return jsonify({"error": f"BIN inválido: {b}. Debe ser 6-15 dígitos numéricos."}), 400

    if count < 1 or count > 50:
        return jsonify({"error": "Cantidad debe estar entre 1 y 50."}), 400

    for _ in range(count):
        selected_bin = random.choice(bins) if bins else "453957"  # Default Visa BIN
        bin_info = get_bin_info(selected_bin)
        length = bin_info['length'] if bin_info else 16
        card_number = generate_luhn(selected_bin, length)

        expiry = custom_date if use_custom_date and custom_date else random_expiry()
        cvv_length = 4 if bin_info and bin_info['brand'] == 'Amex' else 3
        cvv = custom_cvv if use_custom_cvv and custom_cvv else random_cvv(cvv_length)

        profile = {
            'name': fake.name(),
            'dob': fake.date_of_birth(minimum_age=18, maximum_age=90).strftime("%d/%m/%Y"),
            'address': fake.street_address(),
            'city': fake.city(),
            'state': fake.state() if hasattr(fake, 'state') else '',
            'postalcode': fake.postcode(),
            'country': FAKER_LOCALES.get(country, 'Desconocido'),
            'phone': fake.phone_number(),
            'email': fake.email(),
            'company': fake.company(),
            'job': fake.job(),
            'bio': fake.text(max_nb_chars=120),
            'passport': fake.passport_number() if hasattr(fake, 'passport_number') else 'N/A',
            'website': fake.url(),
            'license': generate_fake_license(),
            'ssn': fake.ssn() if hasattr(fake, 'ssn') else 'N/A',
            'twitter': f"@{fake.user_name()}",
            'linkedin': f"https://linkedin.com/in/{fake.user_name()}",
            'iban': generate_fake_iban(),
            'photo': get_user_photo(),
        }

        result_cards.append({
            'number': card_number,
            'expiry': expiry,
            'cvv': cvv,
            'brand': bin_info['brand'] if bin_info else 'Desconocido'
        })
        result_profiles.append(profile)

    return jsonify({
        'cards': result_cards,
        'profiles': result_profiles,
        'locale_name': FAKER_LOCALES.get(country, 'Aleatorio/Default')
    })


TEMPLATE = '''
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>ANDRÔMEDA CC GEN Mejorado</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&display=swap');
    body {
        margin:0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: #121212;
        color: #eee;
        transition: background-color 0.5s, color 0.5s;
    }
    body.light {
        background: #f4f4f4;
        color: #111;
    }
    .banner {
        background: linear-gradient(90deg, #0ff, #00f, #0f0);
        background-size: 300% 300%;
        animation: gradientBG 12s ease infinite;
        padding: 40px 10px;
        text-align: center;
        box-shadow: 0 0 25px #0ff;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 15px;
        flex-wrap: wrap;
    }
    @keyframes gradientBG {
        0%{background-position:0% 50%;}
        50%{background-position:100% 50%;}
        100%{background-position:0% 50%;}
    }
    .banner svg {
        width: 60px; height: 60px;
        fill: #0ff;
        filter: drop-shadow(0 0 5px #0ff);
        animation: spin 10s linear infinite;
    }
    @keyframes spin {
        0%{transform: rotate(0deg);}
        100%{transform: rotate(360deg);}
    }
    .banner h1 {
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
        font-size: 3.4rem;
        letter-spacing: 0.15em;
        margin: 0;
        color: #0ff;
        text-shadow: 0 0 10px #0ff;
    }
    .toggle-theme {
        cursor: pointer;
        background: none;
        border: 2px solid #0ff;
        color: #0ff;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 1.1rem;
        transition: background-color 0.3s, color 0.3s;
    }
    .toggle-theme:hover {
        background: #0ff;
        color: #121212;
    }
    .container {
        max-width: 1100px;
        margin: 30px auto;
        padding: 0 15px 50px 15px;
    }
    form {
        background: #222;
        padding: 25px 30px;
        border-radius: 12px;
        box-shadow: 0 0 25px #0ff5;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 15px 30px;
        align-items: center;
    }
    form label {
        display: flex;
        flex-direction: column;
        font-weight: 600;
        font-size: 1rem;
        color: #aadcee;
    }
    form input, form select {
        margin-top: 6px;
        border: none;
        padding: 10px 12px;
        border-radius: 8px;
        font-size: 1rem;
        background: #121212;
        color: #eee;
        box-shadow: inset 0 0 6px #0ff3;
        transition: background-color 0.3s, color 0.3s;
    }
    form input:focus, form select:focus {
        outline: none;
        box-shadow: inset 0 0 10px #0ff9;
        background: #001f3f;
    }
    form button {
        grid-column: 1/-1;
        padding: 15px 0;
        font-size: 1.2rem;
        font-weight: 700;
        border: none;
        border-radius: 12px;
        background: linear-gradient(90deg, #0ff, #00f, #0f0);
        color: #121212;
        cursor: pointer;
        transition: box-shadow 0.3s ease, transform 0.2s ease;
        user-select: none;
        filter: drop-shadow(0 0 5px #0ff);
    }
    form button:hover {
        box-shadow: 0 0 25px #0ff;
        transform: scale(1.05);
    }
    .results {
        margin-top: 40px;
    }
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 20px;
    }
    .card, .profile {
        background: #222;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 0 15px #0ff7;
        transition: box-shadow 0.3s;
        word-break: break-word;
        position: relative;
    }
    .card:hover, .profile:hover {
        box-shadow: 0 0 25px #0ff;
    }
    .card strong, .profile strong {
        color: #0ff;
    }
    .card .copy-btn, .profile .copy-btn {
        position: absolute;
        top: 12px;
        right: 12px;
        background: #0ff;
        border: none;
        padding: 5px 9px;
        border-radius: 8px;
        color: #121212;
        cursor: pointer;
        font-weight: 700;
        font-size: 0.9rem;
        user-select: none;
        transition: background-color 0.3s ease;
    }
    .card .copy-btn:hover, .profile .copy-btn:hover {
        background: #0cc;
    }
    .profile img {
        width: 100%;
        max-height: 180px;
        object-fit: cover;
        border-radius: 10px;
        margin-bottom: 12px;
        box-shadow: 0 0 10px #0ff;
    }
    footer {
        text-align:center;
        margin: 30px 0 60px;
        font-size: 1rem;
        color: #0ff8;
    }
    footer a {
        color: #0ff;
        text-decoration: none;
        font-weight: 600;
        transition: color 0.3s ease;
    }
    footer a:hover {
        color: #0cc;
    }
    /* Responsive tweaks */
    @media (max-width: 720px) {
        form {
            grid-template-columns: 1fr;
        }
    }
</style>
</head>
<body>
<div class="banner">
    <!-- SVG animado simple estilo futurista -->
    <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" role="img">
        <circle cx="32" cy="32" r="30" stroke="#0ff" stroke-width="4" fill="none"/>
        <path d="M16 32h32M32 16v32" stroke="#0ff" stroke-width="4" stroke-linecap="round"/>
    </svg>
    <h1>ANDRÔMEDA</h1>
    <button class="toggle-theme" id="toggleThemeBtn" title="Cambiar tema">Modo Claro</button>
</div>

<div class="container">
    <form id="genForm" autocomplete="off">
        <label>
            BIN(s) (6-15 dígitos, separados por coma):
            <input type="text" name="bin" id="binInput" placeholder="Ej: 453957,510510,371449" required pattern="[\d,\s]{6,50}" title="Solo números y comas, 6-15 dígitos cada BIN" />
        </label>
        <label>
            Cantidad (max 50):
            <input type="number" name="count" id="countInput" min="1" max="50" value="1" required />
        </label>
        <label>
            País para datos falsos:
            <select name="country" id="countrySelect">
                {% for code, name in locales.items() %}
                <option value="{{code}}">{{name}}</option>
                {% endfor %}
            </select>
        </label>
        <label>
            Fecha de expiración personalizada:
            <input type="checkbox" id="customDateCheckbox" />
            <input type="month" id="customDate" disabled />
        </label>
        <label>
            CVV personalizado:
            <input type="checkbox" id="customCvvCheckbox" />
            <input type="text" id="customCvv" maxlength="4" pattern="\\d{3,4}" placeholder="3 o 4 dígitos" disabled />
        </label>
        <button type="submit">Generar tarjetas</button>
    </form>

    <div class="results" id="results"></div>
</div>

<footer>
    Contacto creador: <a href="https://t.me/LooKsCrazy0" target="_blank">@LooKsCrazy0</a>
</footer>

<script>
    const toggleThemeBtn = document.getElementById('toggleThemeBtn');
    const body = document.body;
    toggleThemeBtn.addEventListener('click', () => {
        if(body.classList.contains('light')) {
            body.classList.remove('light');
            toggleThemeBtn.textContent = "Modo Claro";
        } else {
            body.classList.add('light');
            toggleThemeBtn.textContent = "Modo Oscuro";
        }
    });

    const customDateCheckbox = document.getElementById('customDateCheckbox');
    const customDateInput = document.getElementById('customDate');
    const customCvvCheckbox = document.getElementById('customCvvCheckbox');
    const customCvvInput = document.getElementById('customCvv');

    customDateCheckbox.addEventListener('change', () => {
        customDateInput.disabled = !customDateCheckbox.checked;
        if(!customDateCheckbox.checked) customDateInput.value = "";
    });
    customCvvCheckbox.addEventListener('change', () => {
        customCvvInput.disabled = !customCvvCheckbox.checked;
        if(!customCvvCheckbox.checked) customCvvInput.value = "";
    });

    const form = document.getElementById('genForm');
    const resultsDiv = document.getElementById('results');

    function copyToClipboard(text, btn) {
        navigator.clipboard.writeText(text).then(() => {
            btn.textContent = "¡Copiado!";
            setTimeout(() => btn.textContent = "Copiar", 1500);
        });
    }

    function formatExpiry(input) {
        // input type month returns "YYYY-MM", format to MM/YY
        if(!input) return "";
        const parts = input.split("-");
        if(parts.length !== 2) return "";
        return parts[1].slice(-2) + "/" + parts[0].slice(-2);
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        resultsDiv.innerHTML = "<p>Cargando...</p>";

        const bin = document.getElementById('binInput').value.trim();
        const count = document.getElementById('countInput').value;
        const country = document.getElementById('countrySelect').value;
        const useCustomDate = customDateCheckbox.checked;
        const customDateVal = formatExpiry(customDateInput.value);
        const useCustomCvv = customCvvCheckbox.checked;
        const customCvvVal = customCvvInput.value;

        // Validar BIN simple
        const binsArr = bin.split(",").map(s => s.trim());
        for(let b of binsArr) {
            if(!/^\d{6,15}$/.test(b)) {
                resultsDiv.innerHTML = `<p style="color:#f55;">Error: BIN inválido "${b}". Debe ser entre 6 y 15 dígitos.</p>`;
                return;
            }
        }

        if(useCustomDate && !customDateVal) {
            resultsDiv.innerHTML = `<p style="color:#f55;">Error: Fecha de expiración personalizada inválida.</p>`;
            return;
        }
        if(useCustomCvv && !/^\d{3,4}$/.test(customCvvVal)) {
            resultsDiv.innerHTML = `<p style="color:#f55;">Error: CVV personalizado inválido. Debe ser 3 o 4 dígitos.</p>`;
            return;
        }

        const payload = {
            bin: bin,
            count: count,
            custom_date_checkbox: useCustomDate,
            custom_date: customDateVal,
            custom_cvv_checkbox: useCustomCvv,
            custom_cvv: customCvvVal,
            country: country,
        };

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(payload)
            });
            const json = await response.json();
            if(json.error){
                resultsDiv.innerHTML = `<p style="color:#f55;">Error: ${json.error}</p>`;
                return;
            }
            displayResults(json);
            saveResultsLocally(json);
        } catch (err) {
            resultsDiv.innerHTML = `<p style="color:#f55;">Error al comunicarse con el servidor.</p>`;
            console.error(err);
        }
    });

    function displayResults(data) {
        const cards = data.cards;
        const profiles = data.profiles;
        const localeName = data.locale_name;

        if(cards.length === 0) {
            resultsDiv.innerHTML = "<p>No se generaron tarjetas.</p>";
            return;
        }

        let html = `<h2>Tarjetas generadas (Datos del país: <strong>${localeName}</strong>):</h2>`;
        html += '<div class="grid">';
        for(let i = 0; i < cards.length; i++) {
            const c = cards[i];
            html += `
                <div class="card">
                    <button class="copy-btn" onclick="copyToClipboard('${c.number}', this)">Copiar</button>
                    <p><strong>Tarjeta:</strong> ${c.number}</p>
                    <p><strong>Expiración:</strong> ${c.expiry}</p>
                    <p><strong>CVV:</strong> ${c.cvv}</p>
                    <p><strong>Marca:</strong> ${c.brand}</p>
                </div>
            `;
        }
        html += '</div>';

        html += `<h2>Perfiles falsos asociados:</h2><div class="grid">`;
        for(let p of profiles) {
            html += `
                <div class="profile">
                    ${p.photo ? `<img src="${p.photo}" alt="Foto perfil" loading="lazy" />` : ''}
                    <button class="copy-btn" onclick="copyToClipboard('Nombre: ${p.name}\\nEmail: ${p.email}\\nTel: ${p.phone}', this)">Copiar datos</button>
                    <p><strong>Nombre:</strong> ${p.name}</p>
                    <p><strong>Fecha de Nac.:</strong> ${p.dob}</p>
                    <p><strong>Dirección:</strong> ${p.address}, ${p.city} ${p.state} ${p.postalcode}</p>
                    <p><strong>País:</strong> ${p.country}</p>
                    <p><strong>Teléfono:</strong> ${p.phone}</p>
                    <p><strong>Email:</strong> ${p.email}</p>
                    <p><strong>Empresa:</strong> ${p.company}</p>
                    <p><strong>Trabajo:</strong> ${p.job}</p>
                    <p><strong>Licencia:</strong> ${p.license}</p>
                    <p><strong>IBAN:</strong> ${p.iban}</p>
                    <p><strong>SSN:</strong> ${p.ssn}</p>
                    <p><strong>Twitter:</strong> ${p.twitter}</p>
                    <p><strong>LinkedIn:</strong> <a href="${p.linkedin}" target="_blank">${p.linkedin}</a></p>
                    <p><strong>Web:</strong> <a href="${p.website}" target="_blank">${p.website}</a></p>
                    <p><em>${p.bio}</em></p>
                </div>
            `;
        }
        html += '</div>';

        resultsDiv.innerHTML = html;
    }

    // Guardar resultados localmente para persistir recarga (solo en navegador)
    function saveResultsLocally(data) {
        try {
            localStorage.setItem('andromeda_results', JSON.stringify(data));
        } catch {}
    }
    // Cargar resultados si hay en localStorage
    function loadResultsLocally() {
        try {
            const data = localStorage.getItem('andromeda_results');
            if(data) {
                displayResults(JSON.parse(data));
            }
        } catch {}
    }
    window.onload = () => {
        loadResultsLocally();
    }
</script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True)