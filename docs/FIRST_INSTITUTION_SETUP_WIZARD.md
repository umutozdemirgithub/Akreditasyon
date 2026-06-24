# First Institution Setup Wizard

v118 ile `tenant_default` kaydı artık kullanıcıya hazır tanımlı bir kurum gibi sunulmaz. Sistem bu kaydı yalnızca teknik bootstrap amacıyla tutar.

## Davranış

- Taze kurulumda Süper Admin, Program Yönetimi > Kurum Yönetimi sekmesinde **İlk Kurum Kurulumu** ekranını görür.
- Kurum adı, kısa kod ve domain girilmeden program/fakülte/program kullanıcı sekmeleri açılmaz.
- İlk kurum kaydedildiğinde `tenant_default` gerçek kurum kaydına dönüştürülür ve `setup_completed_at` işaretlenir.
- Bu işlemden sonra normal Kurum Yönetimi ve Yeni Program akışı açılır.

## Amaç

İlk açılışta `Ana Kurum`, `Erciyes Üniversitesi` veya geçmiş volume verisi gibi kayıtların gerçek kurummuş gibi görünmesini engellemek; Super Admin'i kontrollü bir ilk kurulum akışına yönlendirmektir.
