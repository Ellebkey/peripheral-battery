# peripheral-battery

Batería del mouse **Logitech G502 X** y de los audífonos **Corsair VOID WIRELESS v2** en la barra de menú de
macOS (SwiftBar), y en terminal.

```
🎧 65%   🖱 93%
```

## Instalar

```sh
git clone https://github.com/Ellebkey/peripheral-battery.git ~/peripheral-battery
~/peripheral-battery/install.sh
```

`install.sh` hace todo y se puede volver a correr:
1. Comprueba `python3` (si falta: `xcode-select --install`).
2. Instala SwiftBar con Homebrew si no está.
3. Crea `.venv` con `hidapi`.
4. Apunta SwiftBar a `swiftbar/` y lo reinicia.
5. Agrega los alias `mouse-battery` y `headset-battery` a `~/.zshrc` (bloque `# >>> peripheral-battery >>>`).

Después: en SwiftBar activa **Launch at Login**. Si en esa Mac no tienes alguno de los dos aparatos, haz clic en su
ícono → **Disable Plugin**.

Si los íconos se quedan en `–` con el aparato encendido, revisa **Ajustes del Sistema → Privacidad y seguridad →
Monitoreo de entrada** y permite SwiftBar (en la Mac donde se armó no hizo falta).

## Barra de menú
- Un plugin por aparato en `swiftbar/`, refresco cada minuto (el `1m` del nombre). Al hacer clic, detalle y "Actualizar".
- `swiftbar.py <aparato>` corre el lector. Si el aparato no contesta (apagado, dormido o receptor desconectado) no
  imprime nada y SwiftBar oculta el ícono; reaparece en ≤ 1 min. Rojo si ≤ 20 % sin cargar; `⚡` si carga (solo el
  mouse lo reporta).
- El G502 X se duerme tras unos minutos sin moverlo: su ícono desaparece aunque esté prendido y vuelve al moverlo.
- En `swiftbar/` solo van plugins: SwiftBar ejecuta todo archivo ejecutable de esa carpeta.

## Terminal
- `mouse-battery` / `headset-battery` (o `./run.sh mouse|headset`) · `--json`.
- Mouse además: `--all` (DPI, polling rate, firmware; solo lectura) · `--scan` (otros slots del receptor, lento).

## Mouse — Logitech G502 X LIGHTSPEED (receptor `046d:c547`)
- HID++ 2.0: feature Unified Battery (`0x1004`, `getStatus`) del slot 1 del receptor; cae a `0x1000`/`0x1001`.
- Un mouse dormido tarda ~2 s en responder (reintenta solo). Sin respuesta = dormido o apagado.

## Audífonos — Corsair VOID WIRELESS v2 (receptor `1b1c:2a08`)
- Protocolo sacado de HeadsetControl 4.1.0 (`lib/devices/corsair_void_v2w.hpp`), solo lectura: interfaz HID 4,
  reportes de 65 bytes `00 02 <endpoint> <cmd…>` (receptor `0x08`, audífonos `0x09`). Secuencia: firmware del
  receptor `02 13` → heartbeat del receptor `02 12` → heartbeat de los audífonos (sin respuesta = apagados) →
  batería `02 0F` (bytes 4–5, 1–1000, ÷10) → micrófono `02 A6` (arriba = silenciado).
- No pasa el receptor a "software mode" (el `initializeDevice` de HeadsetControl): así no truena el audio, pero
  tampoco puede cambiar sidetone ni el apagado automático (para eso, `headsetcontrol`).
- A veces el receptor contesta con el id del audífono en vez de la batería: se reintenta hasta un valor 1–1000.
- La batería no dice si está cargando.
- También deberían servir el VIRTUOSO MAX (`2a02`) y el HS80 MAX (`0a97`), que HeadsetControl trata igual; no probados.

## Notas
- `hid.read(timeout=0)` de hidapi **bloquea para siempre**: usa `1`–`5` ms para vaciar el buffer.
