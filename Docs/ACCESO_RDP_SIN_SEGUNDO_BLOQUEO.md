# Acceso RDP sin contraseña de desbloqueo

Las conexiones Guacamole de Kali (`192.168.146.134`) y LNX-VICT
(`192.168.146.137`) ya contienen usuario y contraseña válidos. Se comprobó
la autenticación de esas mismas cuentas por SSH, sin mostrar credenciales.
Los escritorios usan XFCE y tienen el bloqueo de pantalla predeterminado.

El ajuste aplicado modifica únicamente cuatro preferencias del usuario RDP:

| Canal | Propiedad | Valor aplicado |
| --- | --- | --- |
| xfce4-screensaver | /lock/enabled | false |
| xfce4-screensaver | /lock/sleep-activation | false |
| xfce4-screensaver | /saver/idle-activation/enabled | false |
| xfce4-power-manager | /xfce4-power-manager/lock-screen-suspend-hibernate | false |

Esto deja las sesiones gráficas abiertas sin pedir contraseña de desbloqueo.
El acceso de la plataforma y las contraseñas de las cuentas permanecen.
Una persona con acceso a una sesión gráfica ya abierta podrá utilizarla.

```bash
python configure_rdp_autoaccess.py --check
python configure_rdp_autoaccess.py --apply
```

El modo predeterminado solo consulta. La aplicación requiere autorización
explícita para este cambio persistente. El script está limitado a los dos
hosts anteriores y usa el bus de las sesiones XFCE de la misma cuenta RDP.
No reinicia servicios ni cierra aplicaciones. Las siete pruebas específicas
pasaron; el modo de consulta fue comprobado con ambas VMs.

Estado: aplicado y verificado en ambas VMs tras la autorización explícita
del usuario. Los cuatro valores quedaron en `false`. No se cambiaron las
contraseñas ni se reiniciaron servicios.

Aceptación visual del 15 de octubre de 2026: Kali abrió el escritorio desde
WEB-02 sin contraseña de desbloqueo. Se comprobó la imagen completa y
centrada al entrar y salir de pantalla completa.

Referencias: [propiedades de Xfce Screensaver](https://raw.githubusercontent.com/xfce-mirror/xfce4-screensaver/master/src/gs-prefs.h)
y [Xfce Power Manager](https://raw.githubusercontent.com/xfce-mirror/xfce4-power-manager/master/common/xfpm-config.h).
