# Tenant Archive Visibility Guard

Bu güncelleme, arşivlenen/silinen kurumların Program Yönetimi ekranlarında görünmeye devam etmesini engeller.

## Düzeltilen davranış

- `Program Yönetimi > Program Kullanıcıları` artık arşivlenmiş kuruma bağlı program kullanıcı kayıtlarını göstermez.
- `Tanımlı Programlar` görünümü arşivlenmiş tenant altında kalan programları liste dışı bırakır.
- Backend sorguları şu kayıtları varsayılan admin listelerinden dışlar:
  - `tenants.deleted_at` dolu tenant kayıtları
  - `programs.deleted_at` dolu programlar
  - `users.deleted_at` dolu kullanıcılar
  - `program_users.deleted_at` dolu program yetkileri

## Not

Soft delete kayıtları geri yükleme/arşiv merkezinde izlenebilir kalır; operasyon ekranlarında aktif kayıt gibi gösterilmez.
