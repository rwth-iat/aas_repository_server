import numpy as np
import matplotlib.pyplot as plt

# Systemmatrix A und Eingangsvektor B
A = np.array([[-2, 2],
              [-2, 2]])
B = np.array([[1],
              [1]])

# Definition der Ableitungsfunktion
def dx_dt(x):
    return np.dot(A, x)

# Erzeugung eines Gitters im Phasenraum
x1 = np.linspace(-10, 10, 20)
x2 = np.linspace(-10, 10, 20)
X1, X2 = np.meshgrid(x1, x2)

# Berechnung der Ableitungen für das Richtungsfeld
U = np.zeros_like(X1)
V = np.zeros_like(X2)
for i in range(len(x1)):
    for j in range(len(x2)):
        x = np.array([[X1[i, j]],
                      [X2[i, j]]])
        dx = dx_dt(x)
        U[i, j] = dx[0]
        V[i, j] = dx[1]

# Plotten des Phasenportraits
plt.figure(figsize=(8, 8))
plt.quiver(X1, X2, U, V, color='b', alpha=0.5)
plt.xlabel('x1')
plt.ylabel('x2')
plt.title('Phasenportrait')
plt.grid(True)
plt.show()
