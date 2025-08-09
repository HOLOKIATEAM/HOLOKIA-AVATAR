#!/usr/bin/env python3
"""
Script de démarrage et monitoring pour tous les services backend
"""

import subprocess
import time
import sys
import os
import signal
import threading
import requests
import json
from pathlib import Path
from datetime import datetime
import psutil

# Configuration des services
SERVICES = {
    "tts": {
        "script": "app/tts_server.py",
        "port": 5000,
        "name": "TTS Server",
        "health_endpoint": "/health",
        "startup_timeout": 30,
        "expected_status": "healthy"
    },
    "stt": {
        "script": "app/stt_server.py", 
        "port": 5002,
        "name": "STT Server",
        "health_endpoint": "/health",
        "startup_timeout": 45,  # Plus long car Whisper doit se charger
        "expected_status": "healthy"
    },
    "main": {
        "script": "app/main.py",
        "port": 5001,
        "name": "Main API",
        "health_endpoint": "/health",
        "startup_timeout": 20,
        "expected_status": "healthy"
    }
}

processes = {}
service_stats = {}
monitoring_active = True

class ServiceMonitor:
    def __init__(self, service_name, service_config, process):
        self.service_name = service_name
        self.service_config = service_config
        self.process = process
        self.start_time = time.time()
        self.last_health_check = None
        self.health_status = "unknown"
        self.response_times = []
        self.error_count = 0
        self.success_count = 0
        
    def get_uptime(self):
        return time.time() - self.start_time
    
    def get_memory_usage(self):
        try:
            if self.process and self.process.poll() is None:
                process = psutil.Process(self.process.pid)
                return process.memory_info().rss / 1024 / 1024  # MB
        except:
            pass
        return 0
    
    def get_cpu_usage(self):
        try:
            if self.process and self.process.poll() is None:
                process = psutil.Process(self.process.pid)
                return process.cpu_percent()
        except:
            pass
        return 0

def start_service(service_name, service_config):
    """Démarre un service avec monitoring"""
    script_path = Path(__file__).parent / service_config["script"]
    
    if not script_path.exists():
        print(f"❌ Script non trouvé : {script_path}")
        return None
    
    print(f"🚀 Démarrage de {service_config['name']} sur le port {service_config['port']}...")
    start_time = time.time()
    
    try:
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        startup_time = time.time() - start_time
        print(f"✅ {service_config['name']} démarré (PID: {process.pid}) en {startup_time:.2f}s")
        
        # Créer le moniteur
        monitor = ServiceMonitor(service_name, service_config, process)
        processes[service_name] = process
        service_stats[service_name] = monitor
        
        return process
    except Exception as e:
        print(f"❌ Erreur lors du démarrage de {service_config['name']} : {e}")
        return None

def check_service_health(service_name, service_config, detailed=False):
    """Vérifie la santé d'un service avec métriques détaillées"""
    monitor = service_stats.get(service_name)
    if not monitor:
        return False
    
    try:
        start_time = time.time()
        response = requests.get(
            f"http://localhost:{service_config['port']}{service_config['health_endpoint']}", 
            timeout=5
        )
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            
            monitor.last_health_check = time.time()
            monitor.health_status = status
            monitor.response_times.append(response_time)
            monitor.success_count += 1
            
            # Garder seulement les 10 derniers temps de réponse
            if len(monitor.response_times) > 10:
                monitor.response_times.pop(0)
            
            if detailed:
                print(f"✅ {service_config['name']} - Status: {status}")
                print(f"   ⏱  Temps de réponse: {response_time:.3f}s")
                print(f"   📊 Uptime: {monitor.get_uptime():.1f}s")
                print(f"   💾 Mémoire: {monitor.get_memory_usage():.1f}MB")
                print(f"   🔄 CPU: {monitor.get_cpu_usage():.1f}%")
                if "languages" in data:
                    print(f"   🌍 Langues: {', '.join(data['languages'])}")
                if "whisper_status" in data:
                    print(f"   🎤 Whisper: {data['whisper_status']}")
                if "gtts_status" in data:
                    print(f"   🔊 gTTS: {data['gtts_status']}")
                if "llm" in data:
                    print(f"   🧠 LLM: {data['llm']}")
            else:
                print(f"✅ {service_config['name']} est en ligne (réponse: {response_time:.3f}s)")
            
            return status == service_config["expected_status"]
        else:
            monitor.error_count += 1
            print(f"⚠  {service_config['name']} répond mais avec un statut {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        monitor.error_count += 1
        print(f"⏰ {service_config['name']} - Timeout lors de la vérification")
        return False
    except Exception as e:
        monitor.error_count += 1
        print(f"❌ {service_config['name']} n'est pas accessible : {e}")
        return False

def monitor_service(service_name, service_config, process):
    """Surveille un service et affiche ses logs en temps réel"""
    if not process:
        return
    
    print(f"📊 Surveillance de {service_config['name']}...")
    
    while process.poll() is None and monitoring_active:
        try:
            # Lire la sortie en temps réel
            output = process.stdout.readline()
            if output:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] [{service_name}] {output.strip()}")
        except:
            break
    
    if process.returncode:
        print(f"❌ {service_config['name']} s'est arrêté avec le code {process.returncode}")

def wait_for_service_startup(service_name, service_config):
    """Attend que le service soit prêt avec timeout"""
    print(f"⏳ Attente du démarrage de {service_config['name']}...")
    
    start_time = time.time()
    timeout = service_config["startup_timeout"]
    
    while time.time() - start_time < timeout:
        if check_service_health(service_name, service_config):
            startup_time = time.time() - start_time
            print(f"✅ {service_config['name']} prêt en {startup_time:.2f}s")
            return True
        time.sleep(1)
    
    print(f"⏰ Timeout: {service_config['name']} n'a pas démarré dans les {timeout}s")
    return False

def print_service_stats():
    """Affiche les statistiques détaillées de tous les services"""
    print("\n" + "="*60)
    print("📊 STATISTIQUES DES SERVICES")
    print("="*60)
    
    for service_name, service_config in SERVICES.items():
        monitor = service_stats.get(service_name)
        if not monitor:
            continue
            
        process = processes.get(service_name)
        is_running = process and process.poll() is None
        
        print(f"\n🔧 {service_config['name']}:")
        print(f"   Status: {'🟢 En ligne' if is_running else '🔴 Arrêté'}")
        print(f"   Uptime: {monitor.get_uptime():.1f}s")
        print(f"   Mémoire: {monitor.get_memory_usage():.1f}MB")
        print(f"   CPU: {monitor.get_cpu_usage():.1f}%")
        print(f"   Vérifications réussies: {monitor.success_count}")
        print(f"   Erreurs: {monitor.error_count}")
        
        if monitor.response_times:
            avg_response = sum(monitor.response_times) / len(monitor.response_times)
            min_response = min(monitor.response_times)
            max_response = max(monitor.response_times)
            print(f"   Temps de réponse - Moy: {avg_response:.3f}s, Min: {min_response:.3f}s, Max: {max_response:.3f}s")

def run_health_check_loop():
    """Boucle de vérification continue de la santé des services"""
    while monitoring_active:
        try:
            print("\n" + "="*60)
            print("🔍 VÉRIFICATION DE LA SANTÉ DES SERVICES")
            print("="*60)
            
            all_healthy = True
            for service_name, service_config in SERVICES.items():
                if not check_service_health(service_name, service_config, detailed=True):
                    all_healthy = False
                print()  # Ligne vide entre services
            
            if all_healthy:
                print("🎉 Tous les services sont en bonne santé !")
            else:
                print("⚠  Certains services ont des problèmes")
            
            print_service_stats()
            
            # Attendre 30 secondes avant la prochaine vérification
            time.sleep(30)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Erreur lors de la vérification : {e}")
            time.sleep(10)

def signal_handler(signum, frame):
    """Gestionnaire de signal pour arrêter proprement les services"""
    global monitoring_active
    print("\n🛑 Arrêt des services...")
    monitoring_active = False
    
    for service_name, process in processes.items():
        if process and process.poll() is None:
            print(f"🛑 Arrêt de {service_name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    
    print_service_stats()
    sys.exit(0)

def test_service_integration():
    """Test d'intégration entre les services"""
    print("\n🧪 TEST D'INTÉGRATION DES SERVICES")
    print("="*60)
    
    # Test 1: Génération de réponse via Main API
    try:
        print("1️⃣ Test de génération de réponse...")
        response = requests.post(
            "http://localhost:5001/api/generate",
            json={
                "history": [
                    {"role": "user", "content": "Bonjour"}
                ],
                "detectedLanguage": "fr"
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Réponse générée: {data.get('text', '')[:50]}...")
        else:
            print(f"❌ Erreur génération: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur test génération: {e}")
    
    # Test 2: Génération TTS
    try:
        print("2️⃣ Test de génération TTS...")
        response = requests.post(
            "http://localhost:5001/api/tts",
            json={
                "text": "Test de synthèse vocale",
                "lang": "fr"
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Audio généré: {data.get('audioId', '')}")
        else:
            print(f"❌ Erreur TTS: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur test TTS: {e}")
    
    # Test 3: Transcription STT
    try:
        print("3️⃣ Test de transcription STT...")
        # Créer un fichier audio de test simple
        test_audio_path = Path(__file__).parent / "app" / "audios" / "test_audio.wav"
        if test_audio_path.exists():
            with open(test_audio_path, "rb") as f:
                files = {"file": ("test.wav", f, "audio/wav")}
                response = requests.post(
                    "http://localhost:5002/transcribe/",
                    files=files,
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Transcription: {data.get('text', '')}")
                else:
                    print(f"❌ Erreur STT: {response.status_code}")
        else:
            print("⚠  Fichier audio de test non trouvé")
    except Exception as e:
        print(f"❌ Erreur test STT: {e}")

def main():
    """Fonction principale avec monitoring complet"""
    print("🎯 Démarrage des services backend avec monitoring...")
    print("="*60)
    
    # Configuration du gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Démarrer tous les services
    startup_success = True
    for service_name, service_config in SERVICES.items():
        process = start_service(service_name, service_config)
        if process:
            # Démarrer la surveillance dans un thread séparé
            monitor_thread = threading.Thread(
                target=monitor_service,
                args=(service_name, service_config, process),
                daemon=True
            )
            monitor_thread.start()
        else:
            startup_success = False
    
    if not startup_success:
        print("❌ Échec du démarrage de certains services")
        return
    
    # Attendre que tous les services démarrent
    print("\n⏳ Attente du démarrage des services...")
    time.sleep(5)
    
    # Vérifier que tous les services sont prêts
    print("\n🔍 Vérification de la santé des services...")
    all_ready = True
    for service_name, service_config in SERVICES.items():
        if not wait_for_service_startup(service_name, service_config):
            all_ready = False
    
    if not all_ready:
        print("❌ Certains services ne sont pas prêts")
        return
    
    print("\n✅ Tous les services sont démarrés !")
    print("📋 Services disponibles :")
    print("   - TTS Server: http://localhost:5000")
    print("   - STT Server: http://localhost:5002") 
    print("   - Main API:  http://localhost:5001")
    print("\n💡 Appuyez sur Ctrl+C pour arrêter tous les services")
    
    # Test d'intégration
    test_service_integration()
    
    # Démarrer la boucle de monitoring
    print("\n🔄 Démarrage du monitoring continu...")
    monitoring_thread = threading.Thread(target=run_health_check_loop, daemon=True)
    monitoring_thread.start()
    
    # Maintenir le script en vie
    try:
        while monitoring_active:
            time.sleep(1)
            # Vérifier si tous les processus sont encore en vie
            for service_name, process in list(processes.items()):
                if process and process.poll() is not None:
                    print(f"❌ {SERVICES[service_name]['name']} s'est arrêté inopinément")
                    processes.pop(service_name, None)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()