import os
import re
from services.firestore_service import FirestoreService

def gs_to_https(gs_url):
    if not gs_url or not gs_url.startswith("gs://"):
        return gs_url
    return gs_url.replace("gs://", "https://storage.googleapis.com/")

def generate_showcase():
    print("🚀 Fetching characters from Firestore...")
    fs = FirestoreService()
    chars_ref = fs.db.collection("characters").stream()
    
    showcase_items = []
    for doc in chars_ref:
        data = doc.to_dict()
        assets = data.get("assets", [])
        if not assets: continue
            
        primary = assets[0]
        dance_url = gs_to_https(primary.get("dance_video"))
        cosplay_url = gs_to_https(primary.get("cosplay_image"))
        if dance_url and cosplay_url:
            showcase_items.append({
                "name": data.get("name", "Unknown"),
                "anime": data.get("anime", ""),
                "image": cosplay_url,
                "video": dance_url
            })

    print(f"📊 Total items found: {len(showcase_items)}")
    
    index_path = os.path.join("docs", "index.html")

    cards_html = ""
    for item in showcase_items:
        cards_html += f"""
            <div class="card" data-tilt>
                <div class="media-container">
                    <img src="{item['image']}" alt="{item['name']}" loading="lazy">
                    <video loop playsinline preload="none" src="{item['video']}"></video>
                    <div class="glow-overlay"></div>
                </div>
                <div class="card-info">
                    <h3>{item['name']}</h3>
                    <span>{item['anime']}</span>
                </div>
            </div>"""

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AURA MACHINE | High-Fashion AI Dance Engine</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
        
        :root {{
            --primary: #ff2d55;
            --secondary: #5856d6;
            --accent: #007aff;
            --bg: #050507;
            --card-bg: rgba(255, 255, 255, 0.03);
            --text: #ffffff;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg);
            color: var(--text);
            overflow-x: hidden;
            line-height: 1.6;
        }}

        #three-canvas {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: -1;
            pointer-events: none;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 40px;
            position: relative;
            z-index: 1;
        }}

        header {{
            padding: 40px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .logo {{
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: -1px;
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 10px 20px rgba(255, 45, 85, 0.2);
        }}

        .sound-toggle {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            color: white;
            padding: 10px 20px;
            border-radius: 100px;
            cursor: pointer;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
            backdrop-filter: blur(10px);
            transition: all 0.3s;
        }}

        .sound-toggle:hover {{
            background: rgba(255,255,255,0.1);
            transform: translateY(-2px);
        }}

        .hero {{
            padding: 80px 0 60px;
            text-align: center;
            perspective: 1000px;
        }}

        .hero h1 {{
            font-size: clamp(3rem, 10vw, 6rem);
            font-weight: 800;
            margin-bottom: 24px;
            letter-spacing: -3px;
            line-height: 1;
            transform-style: preserve-3d;
            animation: float 6s ease-in-out infinite;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0) rotateX(0); }}
            50% {{ transform: translateY(-20px) rotateX(5deg); }}
        }}

        .hero p {{
            font-size: 1.25rem;
            color: rgba(255, 255, 255, 0.6);
            max-width: 800px;
            margin: 0 auto 40px;
            backdrop-filter: blur(5px);
        }}

        .section-title {{
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 50px;
            text-align: center;
            letter-spacing: -1px;
            background: linear-gradient(to right, #fff, rgba(255,255,255,0.3));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        /* Steps Section */
        .steps-container {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 40px 0 80px;
            text-align: left;
        }}

        .step-card {{
            padding: 30px;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 24px;
            transition: all 0.3s ease;
        }}

        .step-num {{
            font-size: 0.8rem;
            font-weight: 800;
            color: var(--primary);
            margin-bottom: 15px;
            letter-spacing: 2px;
        }}

        .step-card h4 {{
            font-size: 1.2rem;
            margin-bottom: 10px;
        }}

        .step-card p {{
            font-size: 0.9rem;
            color: rgba(255,255,255,0.4);
            margin: 0;
            line-height: 1.4;
        }}

        .btn {{
            display: inline-block;
            padding: 20px 40px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            text-decoration: none;
            border-radius: 100px;
            font-weight: 700;
            font-size: 1.1rem;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            backdrop-filter: blur(20px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }}

        .btn.primary {{
            background: linear-gradient(45deg, var(--primary), var(--secondary));
            border: none;
            box-shadow: 0 10px 30px rgba(255, 45, 85, 0.4);
        }}

        .btn:hover {{
            transform: scale(1.1) translateY(-5px);
            box-shadow: 0 30px 60px rgba(255, 45, 85, 0.3);
            border-color: rgba(255,255,255,0.3);
        }}

        /* Grid */
        .showcase {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 40px;
            padding: 0 0 100px;
        }}

        .card {{
            background: var(--card-bg);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 32px;
            padding: 16px;
            transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
            transform-style: preserve-3d;
            cursor: pointer;
            position: relative;
        }}

        .card:hover {{
            border-color: var(--primary);
            background: rgba(255, 255, 255, 0.06);
        }}

        .media-container {{
            position: relative;
            width: 100%;
            aspect-ratio: 4/5;
            overflow: hidden;
            border-radius: 24px;
            background: #000;
            transform: translateZ(20px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }}

        .media-container img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center 15%;
            transition: opacity 0.5s ease;
        }}

        .media-container video {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            object-fit: cover;
            object-position: center 15%;
            opacity: 0;
            transition: opacity 0.5s ease;
        }}

        .card.active .media-container img {{ opacity: 0; }}
        .card.active .media-container video {{ opacity: 1; }}

        .glow-overlay {{
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle at center, transparent 30%, rgba(255, 45, 85, 0.2));
            mix-blend-mode: color-dodge;
            opacity: 0;
            transition: opacity 0.5s;
        }}

        .card:hover {{ transform: scale(1.02); }}

        .card-info {{
            padding: 24px 10px 10px;
            transform: translateZ(30px);
        }}

        .card-info h3 {{
            font-size: 1.4rem;
            margin-bottom: 6px;
            letter-spacing: -0.5px;
        }}

        .card-info span {{
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.4);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }}

        /* Console Section */
        #console {{
            margin: 100px 0;
            padding: 60px;
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 48px;
            backdrop-filter: blur(40px);
        }}

        .footer {{
            padding: 120px 0 60px;
            text-align: center;
            border-top: 1px solid rgba(255,255,255,0.05);
        }}

        .legal-links a {{
            color: white;
            text-decoration: none;
            margin: 0 20px;
            font-weight: 600;
            opacity: 0.5;
            transition: opacity 0.3s;
        }}

        .legal-links a:hover {{ opacity: 1; }}

        @media (max-width: 1100px) {{ 
            .showcase {{ grid-template-columns: 1fr 1fr; }}
            .steps-container {{ grid-template-columns: 1fr 1fr; }}
        }}
        @media (max-width: 700px) {{ 
            .showcase {{ grid-template-columns: 1fr; }} 
            .steps-container {{ grid-template-columns: 1fr; }}
            .container {{ padding: 0 20px; }}
            #console {{ padding: 30px; }}
            .section-title {{ font-size: 2rem; }}
        }}
    </style>
</head>
<body>
    <canvas id="three-canvas"></canvas>

    <div class="container">
        <header>
            <div class="logo">AURA MACHINE</div>
            <button class="sound-toggle" onclick="toggleSound()" id="sound-btn">
                <span>🔇 SOUND OFF</span>
            </button>
        </header>

        <section class="hero">
            <h1>Dance Fashionably.</h1>
            <p>Elevate your aesthetic. <strong>AURA MACHINE</strong> transforms your images into high-fashion dance performances using cutting-edge generative intelligence.</p>
            <div style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; margin-bottom: 40px;">
                <a href="#console" class="btn primary">Launch Aura Dashboard</a>
                <a href="terms.html" class="btn">Protocol Details</a>
            </div>
        </section>

        <!-- SESSION: COSPLAY DANCE -->
        <h2 class="section-title">Cosplay Dance</h2>
        <section id="showcase" class="showcase">
            {cards_html}
        </section>

        <!-- SESSION: PROTOCOL (STEPS) -->
        <h2 class="section-title">The Protocol</h2>
        <div class="steps-container">
            <div class="step-card">
                <div class="step-num">STEP 01</div>
                <h4>Initialize</h4>
                <p>Upload your base image to the machine.</p>
            </div>
            <div class="step-card">
                <div class="step-num">STEP 02</div>
                <h4>Style</h4>
                <p>Select your curated high-fashion outfit.</p>
            </div>
            <div class="step-card">
                <div class="step-num">STEP 03</div>
                <h4>Choreograph</h4>
                <p>Choose your signature dance movement.</p>
            </div>
            <div class="step-card">
                <div class="step-num">STEP 04</div>
                <h4>Manifest</h4>
                <p>Publish your high-fidelity dance remix.</p>
            </div>
        </div>

        <section id="console">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 50px; flex-wrap: wrap; gap: 20px;">
                <div>
                    <h2 style="font-size: 2.5rem; margin-bottom: 10px; letter-spacing: -1px;">Machine Console</h2>
                    <p style="color: rgba(255,255,255,0.4);">Automation protocol for high-fashion content manifest.</p>
                </div>
                <div style="padding: 12px 24px; background: rgba(0,255,100,0.1); border: 1px solid rgba(0,255,100,0.2); border-radius: 100px; color: #00ff64; font-size: 0.95rem; font-weight: 700; letter-spacing: 1px;">
                    ● CORE ONLINE
                </div>
            </div>

            <div style="grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); display: grid; gap: 30px;">
                <div style="padding: 40px; background: rgba(0,0,0,0.4); border-radius: 32px; border: 1px solid rgba(255,255,255,0.05); transform: perspective(1000px) rotateY(3deg);">
                    <div style="margin-bottom: 30px; font-size: 1.5rem; font-weight: 800;">TikTok Bridge</div>
                    <p style="color: rgba(255,255,255,0.4); margin-bottom: 30px;">Grant publishing permissions to the AURA automation cluster.</p>
                    <a href="https://www.tiktok.com/v2/auth/authorize?client_key=YOUR_CLIENT_KEY&scope=user.info.basic,video.publish&response_type=code&redirect_uri=https://dse120071750.github.io/anime-dance-publisher/" 
                       style="display: block; text-align: center; padding: 12px; background: #fff; color: #000; text-decoration: none; border-radius: 16px; font-weight: 800; transition: transform 0.2s;">
                       Authorize Machine
                    </a>
                </div>

                <div style="padding: 40px; background: rgba(255,255,255,0.02); border-radius: 32px; border: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
                    <div style="font-size: 3.5rem; font-weight: 800; color: var(--primary);">124</div>
                    <div style="font-size: 0.9rem; text-transform: uppercase; color: rgba(255,255,255,0.4); letter-spacing: 2px;">Manifestations</div>
                    <div style="margin-top: 30px; padding: 10px 20px; background: rgba(255,255,255,0.05); border-radius: 10px; font-size: 0.8rem;">Processing nodal sync...</div>
                </div>
            </div>
        </section>

        <footer class="footer">
            <div class="legal-links">
                <a href="terms.html">Terms</a>
                <a href="privacy.html">Privacy</a>
                <a href="https://github.com/dse120071750/anime-dance-publisher">Source</a>
            </div>
            <div style="margin-top: 40px; opacity: 0.3; font-size: 0.9rem;">&copy; 2026 AURA MACHINE | HIGH-FASHION DANCE PROTOCOL</div>
        </footer>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vanilla-tilt/1.7.0/vanilla-tilt.min.js"></script>

    <script>
        // --- SOUND LOGIC ---
        let soundEnabled = false;
        function toggleSound() {{
            soundEnabled = !soundEnabled;
            const btn = document.getElementById('sound-btn');
            btn.innerHTML = soundEnabled ? '<span>🔊 SOUND ON</span>' : '<span>🔇 SOUND OFF</span>';
            
            // Apply to currently playing video
            if (currentlyPlayingCard) {{
                const video = currentlyPlayingCard.querySelector('video');
                if (video) video.muted = !soundEnabled;
            }}
        }}

        // --- THREE.JS BACKGROUND ---
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({{ canvas: document.getElementById('three-canvas'), alpha: true, antialias: true }});
        renderer.setSize(window.innerWidth, window.innerHeight);

        const particlesCount = 2000;
        const posArray = new Float32Array(particlesCount * 3);
        const colorArray = new Float32Array(particlesCount * 3);
        
        for(let i=0; i < particlesCount * 3; i+=3) {{
            posArray[i] = (Math.random() - 0.5) * 10;
            posArray[i+1] = (Math.random() - 0.5) * 10;
            posArray[i+2] = (Math.random() - 0.5) * 10;
            colorArray[i] = 1;
            colorArray[i+1] = Math.random() < 0.5 ? 0.17 : 0.34;
            colorArray[i+2] = Math.random() < 0.5 ? 0.33 : 0.84;
        }}
        
        const particlesGeometry = new THREE.BufferGeometry();
        particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
        particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));
        const particlesMaterial = new THREE.PointsMaterial({{ size: 0.006, vertexColors: true, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending }});
        const particlesMesh = new THREE.Points(particlesGeometry, particlesMaterial);
        scene.add(particlesMesh);
        camera.position.z = 3;

        let mouseX = 0, mouseY = 0;
        document.addEventListener('mousemove', (e) => {{
            mouseX = (e.clientX / window.innerWidth) - 0.5;
            mouseY = (e.clientY / window.innerHeight) - 0.5;
        }});

        function animate() {{
            requestAnimationFrame(animate);
            particlesMesh.rotation.y += 0.0008;
            particlesMesh.rotation.x += 0.0003;
            particlesMesh.position.x += (mouseX * 0.4 - particlesMesh.position.x) * 0.02;
            particlesMesh.position.y += (-mouseY * 0.4 - particlesMesh.position.y) * 0.02;
            renderer.render(scene, camera);
        }}
        animate();

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }});

        VanillaTilt.init(document.querySelectorAll("[data-tilt]"), {{
            max: 12, speed: 600, glare: true, "max-glare": 0.15, gyroscope: true, scale: 1.02
        }});

        // --- INTERACTIVE CARDS ---
        let currentlyPlayingCard = null;
        function playCard(card) {{
            if (currentlyPlayingCard === card) return;
            if (currentlyPlayingCard) {{
                const prevVideo = currentlyPlayingCard.querySelector('video');
                currentlyPlayingCard.classList.remove('active');
                if (prevVideo) {{
                    prevVideo.pause();
                    prevVideo.muted = true;
                }}
            }}
            const video = card.querySelector('video');
            if (video) {{
                currentlyPlayingCard = card;
                card.classList.add('active');
                video.currentTime = 0;
                video.muted = !soundEnabled; // Sync with sound toggle
                video.play().catch(e => {{
                    console.log('Autoplay blocked with sound, standard behavior.');
                    video.muted = true; // Fallback to mute to ensure play
                    video.play();
                }});
            }}
        }}

        function stopCard(card) {{
            if (currentlyPlayingCard === card) {{
                const video = card.querySelector('video');
                card.classList.remove('active');
                if (video) {{
                    video.pause();
                    video.muted = true;
                }}
                currentlyPlayingCard = null;
            }}
        }}

        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) playCard(entry.target);
                else if (currentlyPlayingCard === entry.target) stopCard(entry.target);
            }});
        }}, {{ threshold: 0.7 }});

        document.querySelectorAll('.card').forEach(card => {{
            observer.observe(card);
            card.addEventListener('mouseenter', () => playCard(card));
            card.addEventListener('mouseleave', () => stopCard(card));
        }});
    </script>
</body>
</html>"""

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"✨ AURA MACHINE 2.1: Sound Protocol + Redefined Session Hierarchy.")

if __name__ == "__main__":
    generate_showcase()
