import tensorflow as tf

pi = 3.141592653589793
U = 32768.0

tfand = tf.logical_and

class TutorialBotOutput:

    def __init__(self, batch_size):
        self.batch_size = batch_size
        global zero,zeros3,one
        zero = tf.zeros(self.batch_size, tf.float32)
        zeros3 = [zero,zero,zero]
        one = zero + 1

    def get_output_vector(self, values):

        steer = pitch = yaw = roll = throttle = boost = jump = powerslide = zero

        player, ball = values.gamecars[0], values.gameball

        pL,pV,pR = a3(player.Location), a3(player.Velocity), a3(player.Rotation)
        paV,pB = a3(player.AngularVelocity), tf.cast(player.Boost,tf.float32)
        poG,pJ = tf.cast(player.bOnGround,tf.bool), tf.cast(player.bJumped,tf.bool)
        pdJ = tf.cast(player.bDoubleJumped,tf.bool)
        bL,bR,bV = a3(ball.Location), a3(ball.Rotation), a3(ball.Velocity)

        pxv,pyv,pzv = local(pV,zeros3,pR)
        pvd,pva,pvi = spherical(pxv,pyv,pzv)
        iv,rv,av = local(paV,zeros3,pR)

        tx,ty,tz = local(bL,pL,pR)
        txv,tyv,tzv = local(bV,zeros3,pR)
        xv,yv,zv = pxv-txv, pyv-tyv, pzv-tzv

        dT = (.5*tf.abs(ty) + .9*tf.abs(tx) + .4*tf.abs(tz))/1500.0
        tL = predict_(bL,bV,dT*1.3)

        tL = tif(tfand(tf.logical_not(poG),pL[2]>150), tL-predict_(zeros3,pV,dT), tL)
        tx,ty,bz = local(tL,pL,pR)
        td,ta,ti = spherical(tx,ty,tz)

        # aim
        goal = a3([zero,5250*one,300*one])
        gtL = tL - goal
        gpL = pL - goal
        gtd,gta,gti = spherical(gtL[0],gtL[1],gtL[2],0)
        gpd,gpa,gpi = spherical(gpL[0],gpL[1],gpL[2],0)
        gtd += 110
        tL = cartesian(gtd,gta,gti) + goal

        x,y,z = local(tL,pL,pR)
        d,a,i = spherical(x,y,z)
        d2 = tf.sqrt(x*x+y*y)
        d22 = tf.sqrt((x-pxv*dT)**2+(y-pyv*dT)**2)
        r = pR[2]/U

        # controls
        throttle = regress((y-yv*.23*tf.cast(tf.abs(z)<70,tf.float32))/900.0)
        steer = regress(a-av/45.0)
        yaw = regress(a-av/13.0)
        pitch = regress(-i-iv/15.0)
        roll = regress(-r+rv/22.0)

        boost = tf.cast( tfand( tf.abs(a)<.15, tfand( throttle>.5, tf.abs(i)<.25 )), tf.float32)

        # general powerslide
        powerslide = tf.cast( tfand(a*steer>=0, tfand( .15<abs(a-av/35), tfand(abs(a-av/35)<.85,
                              tfand( x*xv>=0,tfand( y*yv>=0, a*av>=0 ))))), tf.float32)

       # powerslide 180°
        pcond1 = tfand(d2>400, abs(a+av/2.25)>0.45)
        pcond2 = tfand(d2>700,  pyv<-90)
        pcond3 = tfand(abs(a)<0.98, abs(av)>0.5)
        pcond4 = tfand(d2>900, tfand(abs(a)<0.95, pyv<1000))

        steer = tif( tfand(pcond1,abs(a)>0.98), one, steer)
        steer = tif( tfand(pcond1,pcond2), -tf.sign(steer), steer)
        powerslide = tif( tfand(pcond1,tfand(pcond2,pcond3)), one, powerslide)
        throttle = tif( tfand(pcond1,tfand(tf.logical_not(pcond2),pcond4)), one, throttle)

        # three point turn
        tptcond = ( tfand( 95<abs(x), tfand( abs(x)<450, tfand( abs(y)<200, tfand(.35<abs(a), 
                    tfand( abs(a)<.65, tfand( abs(pyv)<550, abs(yv)<550 )))))) )

        throttle = tif(tptcond, -tf.sign(throttle), throttle)
        steer = tif(tptcond, -tf.sign(steer), steer)

        # single jump
        jump = ( tf.cast( tfand(150<z, tfand(z<400 , tfand(d22<300, tf.abs(a-pva)<.03 ))), 
                 tf.float32) )

        jump = tif( fwcond, one, jump)
        pitch = tif( fwcond, tf.abs(a)*2 -1, pitch)
        yaw = tif( fwcond, zero, yaw)
        roll = tif( fwcond, zero, roll)

        # dodge
        dgcond = tfand(d22<150, tfand(tf.abs(z)<150, tfand( Range180(gta-gpa,1)<.05,
                 tfand( gtd<gpd,tf.logical_not(pdJ) ))))

        jump = tif( tfand(dgcond, poG), one, jump)
        jump = tif( tfand(dgcond, tfand(tf.logical_not(poG),pzv%10>5 )), zero, jump)
        jump = tif( tfand(dgcond, tfand(tf.logical_not(poG),pzv%10<=5 )), one, jump)
        pitch = tif( tfand(dgcond, tfand(tf.logical_not(poG),pzv%10<=5 )), tf.abs(ta)*2 -1, pitch)
        yaw = tif( tfand(dgcond, tfand(tf.logical_not(poG),pzv%10<=5 )), tf.abs( Range180(ta+0.5,1)*2 ) - 1, yaw)
        roll = tif( tfand(dgcond, tfand(tf.logical_not(poG),pzv%10<=5 )), zero, roll)


        output = [throttle, steer, pitch, yaw, roll, jump, boost, powerslide]

        return output

def a3(V):
    try : a = tf.stack([V.X,V.Y,V.Z])
    except :
        try :a = tf.stack([V.Pitch,V.Yaw,V.Roll])
        except : a = tf.stack([V[0],V[1],V[2]])
    return tf.cast(a,tf.float32)

def Range180(value,pi):
    value = value - tf.abs(value)//(2.0*pi) * (2.0*pi) * tf.sign(value)
    value = value - tf.cast(tf.greater( tf.abs(value), pi),tf.float32) * (2.0*pi) * tf.sign(value)
    return value

def Range(value,R):
    return tif( tf.abs(value)>R, tf.sign(value)*R, value)

def rotate2D(x,y,ang):
    x2 = x*tf.cos(ang) - y*tf.sin(ang)
    y2 = y*tf.cos(ang) + x*tf.sin(ang)
    return x2,y2

def local(tL,oL,oR,Urot=True):
    L = tL-oL
    if Urot :
        pitch = oR[0]*pi/U
        yaw = Range180(oR[1]-U/2,U)*pi/U
        roll = oR[2]*pi/U
        R = -tf.stack([pitch,yaw,roll])
    else :
        R = -oR
    x,y = rotate2D(L[0],L[1],R[1])
    y,z = rotate2D(y,L[2],R[0])
    x,z = rotate2D(x,z,R[2])
    return x,y,z

def spherical(x,y,z,Urot=True):
    d = tf.sqrt(x*x+y*y+z*z)
    try : i = tf.acos(z/d)
    except: i=0
    a = tf.atan2(y,x)
    if Urot : return d, Range180(a/pi-.5,1), Range180(i/pi-.5,1)
    else : return d,a,i

def cartesian(d,a,i):
    x = d * tf.sin(i) * tf.cos(a)
    y = d * tf.sin(i) * tf.sin(a)
    z = d * tf.cos(i)
    return x,y,z

def d3(A,B=[0,0,0]):
    A,B = a3(A),a3(B)
    return tf.sqrt((A[0]-B[0])**2+(A[1]-B[1])**2+(A[2]-B[2])**2)

def tif(cond, iftrue, iffalse):
  cond = tf.cast(cond, tf.float32)
  return cond*iftrue + (1-cond)*iffalse

def regress(a):
    return tif(abs(a)>.1, tf.sign(a), 10*a)

def predict_(L0,V0,dt):
    r = 0.03
    g = a3([zero,zero,zero-650.0])

    A = g -r*V0
    nL = L0 + V0*dt + .5*A*dt**2

    return nL
