import os

WORLD_PATH = r"C:\Users\Sebas\Desktop\SIMULACION FINAL\worlds\cienaga.wbt"

WORLD_CONTENT = """#VRML_SIM R2025a utf8

WorldInfo {
  info [
    "Sistema de Vigilancia con Drones - Cienaga, Magdalena"
    "Simulacion de patrullaje autonomo urbano (Modo Offline)"
    "Desarrollado con Webots R2025a"
  ]
  title "Vigilancia Drone - Cienaga, Magdalena"
  basicTimeStep 8
  coordinateSystem "NUE"
  defaultDamping Damping {
    linear 0.5
    angular 0.5
  }
}

Viewpoint {
  orientation -0.3826834323650904 0 0.9238795325112867 1.5707963267948966
  position 0 120 80
  near 0.1
  follow "Drone_1"
  followSmoothness 0.2
}

Background {
  skyColor [ 0.4 0.6 0.9 ]
}

DirectionalLight {
  direction -0.5 -1 -0.5
  intensity 2.0
  castShadows TRUE
}

# =====================================================
# CIUDAD 3D (Malla OBJ) - Escalada 3x (1 solo modelo)
# =====================================================
Solid {
  translation 0 0 0
  children [
    Transform {
      scale 3 3 3
      children [
        CadShape {
          url [
            "../uploads_files_6462436_uploads_files_328363_SimplePoly_City.OBJ/SimplePoly City.FBX/Scene/Scene_City.obj"
          ]
          castShadows FALSE
        }
      ]
    }
  ]
  name "escenario_ciudad"
}


# =====================================================
# ILUMINACION
# =====================================================
PointLight { location 20 6 0 intensity 3 radius 20 color 1 0.95 0.8 attenuation 0 0 1 }
PointLight { location -20 6 0 intensity 3 radius 20 color 1 0.95 0.8 attenuation 0 0 1 }
PointLight { location 0 6 20 intensity 3 radius 20 color 1 0.95 0.8 attenuation 0 0 1 }
PointLight { location 0 6 -20 intensity 3 radius 20 color 1 0.95 0.8 attenuation 0 0 1 }

# =====================================================
# DRONES (Implementacion Custom sin EXTERNPROTO)
# =====================================================

DEF DRONE_PROTO Robot {
  translation -5 0.5 -5
  name "Drone_1"
  controller "drone_controller"
  controllerArgs ["--id=1" "--zone=norte"]
  supervisor TRUE
  customData "patrol_zone:norte"

  children [
    Shape {
      appearance PBRAppearance { baseColor 0.8 0.8 0.8 roughness 0.5 metalness 0.8 }
      geometry Box { size 0.9 0.3 0.9 }
    }
    Shape {
      appearance PBRAppearance { baseColor 0.2 0.2 0.2 }
      geometry Cylinder { radius 0.06 height 1.8 }
      castShadows FALSE
    }
    Transform {
      rotation 1 0 0 1.5708
      children [
        Shape {
          appearance PBRAppearance { baseColor 0.2 0.2 0.2 }
          geometry Cylinder { radius 0.06 height 1.8 }
          castShadows FALSE
        }
      ]
    }
    Camera { name "camera" translation 0 0 -0.16 fieldOfView 1.2 width 400 height 240 }
    GPS { name "gps" }
    InertialUnit { name "inertial unit" }
    Gyro { name "gyro" }
    Compass { name "compass" }
    Emitter { name "emitter_d1" channel 1 range 200 }
    Receiver { name "receiver_d1" channel 10 bufferSize 256 }
    HingeJoint {
      jointParameters HingeJointParameters { axis 0 1 0 anchor 0.45 0.3 -0.45 }
      device [ RotationalMotor { name "front right propeller" maxVelocity 600 } ]
      endPoint Solid { name "arm_1"
        translation 0.45 0.3 -0.45
        children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.3 height 0.03 } } ]
        boundingObject Cylinder { radius 0.3 height 0.03 }
        physics Physics { density -1 mass 0.05 }
      }
    }
    HingeJoint {
      jointParameters HingeJointParameters { axis 0 1 0 anchor -0.45 0.3 -0.45 }
      device [ RotationalMotor { name "front left propeller" maxVelocity 600 } ]
      endPoint Solid { name "arm_2"
        translation -0.45 0.3 -0.45
        children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.3 height 0.03 } } ]
        boundingObject Cylinder { radius 0.3 height 0.03 }
        physics Physics { density -1 mass 0.05 }
      }
    }
    HingeJoint {
      jointParameters HingeJointParameters { axis 0 1 0 anchor 0.45 0.3 0.45 }
      device [ RotationalMotor { name "rear right propeller" maxVelocity 600 } ]
      endPoint Solid { name "arm_3"
        translation 0.45 0.3 0.45
        children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.3 height 0.03 } } ]
        boundingObject Cylinder { radius 0.3 height 0.03 }
        physics Physics { density -1 mass 0.05 }
      }
    }
    HingeJoint {
      jointParameters HingeJointParameters { axis 0 1 0 anchor -0.45 0.3 0.45 }
      device [ RotationalMotor { name "rear left propeller" maxVelocity 600 } ]
      endPoint Solid { name "arm_4"
        translation -0.45 0.3 0.45
        children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.3 height 0.03 } } ]
        boundingObject Cylinder { radius 0.3 height 0.03 }
        physics Physics { density -1 mass 0.05 }
      }
    }
  ]
  boundingObject Box { size 0.9 0.3 0.9 }
  physics Physics { density -1 mass 1.0 }
}

Robot {
  translation 5 0.5 -5
  rotation 0 1 0 1.5708
  name "Drone_2"
  controller "drone_controller"
  controllerArgs ["--id=2" "--zone=sur"]
  supervisor TRUE
  customData "patrol_zone:sur"
  children [
    Shape { appearance PBRAppearance { baseColor 0.9 0.4 0.1 roughness 0.5 metalness 0.8 } geometry Box { size 0.9 0.3 0.9 } }
    Shape { appearance PBRAppearance { baseColor 0.2 0.2 0.2 } geometry Cylinder { radius 0.06 height 1.8 } castShadows FALSE }
    Transform { rotation 1 0 0 1.5708 children [ Shape { appearance PBRAppearance { baseColor 0.2 0.2 0.2 } geometry Cylinder { radius 0.06 height 1.8 } castShadows FALSE } ] }
    Camera { name "camera" translation 0 0 -0.16 fieldOfView 1.2 width 400 height 240 }
    GPS { name "gps" }
    InertialUnit { name "inertial unit" }
    Gyro { name "gyro" }
    Compass { name "compass" }
    Emitter { name "emitter_d2" channel 2 range 200 }
    Receiver { name "receiver_d2" channel 10 bufferSize 256 }
    HingeJoint { jointParameters HingeJointParameters { axis 0 1 0 anchor 0.45 0.3 -0.45 } device [ RotationalMotor { name "front right propeller" maxVelocity 600 } ] endPoint Solid { name "arm_5" translation 0.45 0.3 -0.45 children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.3 height 0.03 } } ] boundingObject Cylinder { radius 0.3 height 0.03 } physics Physics { density -1 mass 0.05 } } }
    HingeJoint { jointParameters HingeJointParameters { axis 0 1 0 anchor -0.45 0.3 -0.45 } device [ RotationalMotor { name "front left propeller" maxVelocity 600 } ] endPoint Solid { name "arm_6" translation -0.45 0.3 -0.45 children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.3 height 0.03 } } ] boundingObject Cylinder { radius 0.3 height 0.03 } physics Physics { density -1 mass 0.05 } } }
    HingeJoint { jointParameters HingeJointParameters { axis 0 1 0 anchor 0.45 0.3 0.45 } device [ RotationalMotor { name "rear right propeller" maxVelocity 600 } ] endPoint Solid { name "arm_7" translation 0.45 0.3 0.45 children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.3 height 0.03 } } ] boundingObject Cylinder { radius 0.3 height 0.03 } physics Physics { density -1 mass 0.05 } } }
    HingeJoint { jointParameters HingeJointParameters { axis 0 1 0 anchor -0.45 0.3 0.45 } device [ RotationalMotor { name "rear left propeller" maxVelocity 600 } ] endPoint Solid { name "arm_8" translation -0.45 0.3 0.45 children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.3 height 0.03 } } ] boundingObject Cylinder { radius 0.3 height 0.03 } physics Physics { density -1 mass 0.05 } } }
  ]
  boundingObject Box { size 0.9 0.3 0.9 }
  physics Physics { density -1 mass 1.0 }
}

Robot {
  translation 0 0.5 5
  rotation 0 1 0 3.14159
  name "Drone_3"
  controller "drone_controller"
  controllerArgs ["--id=3" "--zone=central"]
  supervisor TRUE
  customData "patrol_zone:central"
  children [
    Shape { appearance PBRAppearance { baseColor 0.5 0.2 0.8 roughness 0.5 metalness 0.8 } geometry Box { size 0.9 0.3 0.9 } }
    Shape { appearance PBRAppearance { baseColor 0.2 0.2 0.2 } geometry Cylinder { radius 0.06 height 1.8 } castShadows FALSE }
    Transform { rotation 1 0 0 1.5708 children [ Shape { appearance PBRAppearance { baseColor 0.2 0.2 0.2 } geometry Cylinder { radius 0.06 height 1.8 } castShadows FALSE } ] }
    Camera { name "camera" translation 0 0 -0.16 fieldOfView 1.2 width 400 height 240 }
    GPS { name "gps" }
    InertialUnit { name "inertial unit" }
    Gyro { name "gyro" }
    Compass { name "compass" }
    Emitter { name "emitter_d3" channel 3 range 200 }
    Receiver { name "receiver_d3" channel 10 bufferSize 256 }
    HingeJoint { jointParameters HingeJointParameters { axis 0 1 0 anchor 0.45 0.3 -0.45 } device [ RotationalMotor { name "front right propeller" maxVelocity 600 } ] endPoint Solid { name "arm_9" translation 0.45 0.3 -0.45 children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.3 height 0.03 } } ] boundingObject Cylinder { radius 0.3 height 0.03 } physics Physics { density -1 mass 0.05 } } }
    HingeJoint { jointParameters HingeJointParameters { axis 0 1 0 anchor -0.15 0.1 -0.15 } device [ RotationalMotor { name "front left propeller" maxVelocity 600 } ] endPoint Solid { name "arm_10" translation -0.15 0.1 -0.15 children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.1 height 0.01 } } ] boundingObject Cylinder { radius 0.1 height 0.01 } physics Physics { density -1 mass 0.05 } } }
    HingeJoint { jointParameters HingeJointParameters { axis 0 1 0 anchor 0.15 0.1 0.15 } device [ RotationalMotor { name "rear right propeller" maxVelocity 600 } ] endPoint Solid { name "arm_11" translation 0.15 0.1 0.15 children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.1 height 0.01 } } ] boundingObject Cylinder { radius 0.1 height 0.01 } physics Physics { density -1 mass 0.05 } } }
    HingeJoint { jointParameters HingeJointParameters { axis 0 1 0 anchor -0.15 0.1 0.15 } device [ RotationalMotor { name "rear left propeller" maxVelocity 600 } ] endPoint Solid { name "arm_12" translation -0.15 0.1 0.15 children [ Shape { appearance PBRAppearance { baseColor 0.1 0.1 0.1 } geometry Cylinder { radius 0.1 height 0.01 } } ] boundingObject Cylinder { radius 0.1 height 0.01 } physics Physics { density -1 mass 0.05 } } }
  ]
  boundingObject Box { size 0.3 0.1 0.3 }
  physics Physics { density -1 mass 1.0 }
}

# =====================================================
# SUPERVISOR — Centro de Control
# =====================================================
Robot {
  name "CentroControl"
  controller "control_center"
  supervisor TRUE
  children [
    Receiver { name "receptor_central" channel -1 bufferSize 1024 }
    Emitter { name "emisor_central" channel 10 range 300 }
  ]
}
"""

with open(WORLD_PATH, "w", encoding="utf-8") as f:
    f.write(WORLD_CONTENT)

print(f"Archivo {WORLD_PATH} restaurado al estado original.")
