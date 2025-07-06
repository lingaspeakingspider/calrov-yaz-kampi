# İletişim ve Kontrol Ödevi:

1. Udp ile mavlink bağlantısı kurulsun. (Local IP adresi)
2. mavproxy kurup localhosta bağlanın. (İnternette dokümantasyonu var takılırsanız oradan bakabilirsiniz)
3. İlk başta heartbeat mesajı bekleyip sonrasında mesaj alma yapılacak (wait heartbeat())
4. Mesaj alma işleminde "HEARTBEAT" türünde mesaj alınacak ve herhangi bir txt dosyasına sözlük şeklinde gelen mesaj yazdırılacak. (Bu sonsuz bir döngüde yapılacak)
5. Bir klavye modu yapılacak ve program başladığında otomatik olarak klavye modu da başlayacak. Aşağıda tuşlara atanacak fonksiyonlar verilmiştir:
	- W, A, S, D: ileri, sol, geri, sağ
	- Arrow key up, Arrow key down: yukarı, aşağı
	- Arrow key right, Arrow key left: sağ yaw ekseni, sol yaw ekseni
	- Q: Arm
	- E: Disarm
	- 1, 2, 3: (sırasıyla) Manual, Depth Hold, Stabilize Modları
	- Esc: Klavye modundan çıkış
	- Z: Servo motora komut gönderme (mesaj türü: MAV_CMD_DO_SET_SERVO)
	
6. Klavye modunda hareket komutları mavlink ile verilecek ve verildiğinde x, y, z ve yaw değerleri ekranda gösterilecek. Ekranda gösterirken print() fonksiyonu değil "logging" kütüphanesi kullanılacak. Arm, disarm ve mod komutları da yine mavlink ile verilecek ve yine logging kütüphanesi ile ekrana yazdırılacak. Klavye modu çalışırken arka planda aynı anda heartbeat mesajının txt dosyasına yazdırılması da çalışacak. Bu ikisini aynı anda çalıştırmak için threading ve multiprocessing kütüphaneleri kullanılabilir. Servo motora komut göndermede ise verilen mesaj türü kullanılarak mavlink ile komut gönderilecek. 


# Kullanım

1. Gerekli paketlerin yüklü olduğundan emin ol ve kontrol et.

2. İlk terminal sekmesinde dummy.py dosyasını çalıştır. `py dummy.py`

3. Yeni bir terminal sekmesi aç ve `py -m MAVProxy.mavproxy --master=udp:127.0.0.1:14550 --out=udp:127.0.0.1:14551` komutunu çalıştır. Bu sayede iki port(dummy.py ve connection.py) arasında veri aktarımı sağlanacak.

4. Son bir terminal sekmesi daha aç ve connection.py dosyasını çalıştır. `py connection.py`