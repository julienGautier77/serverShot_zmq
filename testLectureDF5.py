import h5py
folderpath = 'X:/Data/2026/test/2026_01_06/'
fichierHDF5= folderpath + "MotorsPosition_2026_01_06.hdf5"
def printHDF5Structure(fichierHDF5):
    """Affiche la structure complète du fichier HDF5"""
    def print_structure(name, obj):
        indent = "  " * name.count('/')
        if isinstance(obj, h5py.Group):
            print(f"{indent}📂 {name.split('/')[-1]}/")
            # Afficher les attributs du groupe
            if obj.attrs:
                for key, value in obj.attrs.items():
                    print(f"{indent}  📋 {key}: {value}")
        elif isinstance(obj, h5py.Dataset):
            print(f"{indent}📊 {name.split('/')[-1]}")
            # Afficher les attributs du dataset
            for key, value in obj.attrs.items():
                print(f"{indent}  📋 {key}: {value}")
            print(f"{indent}  💾 Data: {obj[()]}")
    
    with h5py.File(fichierHDF5, 'r') as f:
        print(f"📁 {fichierHDF5}")
        f.visititems(print_structure)

# Utilisation :
printHDF5Structure(fichierHDF5)

def readMotorPositionSimple(fichierHDF5, shoot_number, rack_ip, motor_name):
    """
    Version simplifiée qui retourne (position, motor_name, rack_ip)
    """
    try:
        with h5py.File(fichierHDF5, 'r') as hdf_file:
            shoot_groups = [g for g in hdf_file.keys() if g.startswith(f"Shoot_{shoot_number}_")]
            
            if not shoot_groups:
                return None
            
            shoot_group = hdf_file[shoot_groups[0]]
            
            for rack_name in shoot_group.keys():
                rack = shoot_group[rack_name]
                if rack.attrs['ip'] == rack_ip:
                    for motor_key in rack.keys():
                        if rack[motor_key].attrs['name'] == motor_name:
                            position = rack[motor_key].attrs['position']
                            rack_display = rack_name.replace("Rack_", "")
                            return (position, motor_name, rack_ip, rack_display)
            return None
            
    except Exception as e:
        print(f"Erreur: {e}")
        return None

# Utilisation :

result = readMotorPositionSimple(fichierHDF5, 519, "10.0.1.31", "P1 OAP Vert")
if result:
    position, motor, ip, rack = result
    print(f"position du moteur : {motor} sur rack {rack} ({ip}): {position}")



def compareMotorPositions(fichierHDF5, shoot_numbers, rack_ip, motor_name):
    """
    Compare la position d'un moteur sur plusieurs tirs
    """
    print(f"\n📊 Comparaison - Moteur: {motor_name} sur Rack: {rack_ip}")
    print("="*70)
    print(f"{'Shoot':<10} {'Date/Heure':<25} {'Position':<15} {'Δ Position'}")
    print("-"*70)
    
    positions = []
    for shoot in shoot_numbers:
        data = readMotorPositionSimple(fichierHDF5, shoot, rack_ip, motor_name)
        if data:
            pos = data['position']
            positions.append(pos)
            delta = pos - positions[0] if len(positions) > 1 else 0
            delta_str = f"{delta:+.2f}" if delta != 0 else "-"
            print(f"{shoot:<10} {data['timestamp']:<25} {pos:<15.2f} {delta_str}")
    
    print("="*70 + "\n")

# Utilisation :
compareMotorPositions(fichierHDF5, 
                      [519, 520, 521, 522], 
                      "10.0.1.31", "P1 OAP Vert")