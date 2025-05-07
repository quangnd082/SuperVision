import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader

# ✅ 1️⃣ Mô hình Convolutional VAE
class ConvVAE(nn.Module):
    def __init__(self, latent_dim=20, input_size=128):
        super(ConvVAE, self).__init__()
        self.latent_dim = latent_dim
        self.input_size = input_size

        # 🔹 Encoder (2 Conv2D layers)
        self.encoder = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, stride=2, padding=1),  # 128 -> 64
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),  # 64 -> 32
            nn.ReLU(),
            nn.Flatten()
        )

        self.last_size = int(input_size/4)

        self.fc_mu = nn.Linear(64 * self.last_size * self.last_size, latent_dim)      # Mean vector
        self.fc_logvar = nn.Linear(64 * self.last_size * self.last_size, latent_dim)
        # 
        # self.fc_mu_logvar = nn.Linear(64 * self.last_size * self.last_size, latent_dim + latent_dim)  # Log variance vector

        # 🔹 Decoder (Fully Connected + 2 ConvTranspose)
        self.fc_decoder = nn.Linear(latent_dim, 64 * self.last_size * self.last_size)
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(64, 32, kernel_size=3, stride=2, padding=1, output_padding=1),  # (7x7) -> (14x14)
            nn.ReLU(),
            nn.ConvTranspose2d(32, 1, kernel_size=3, stride=2, padding=1, output_padding=1),  # (14x14) -> (28x28)
            # nn.Sigmoid()  # Normalize output [0,1]
        )

    def encode(self, x):
        x = self.encoder(x)
        return self.fc_mu(x), self.fc_logvar(x)

        # x = self.encoder(x)
        # mu_logvar = self.fc_mu_logvar(x)
        # mu, logvar = torch.split(mu_logvar, self.latent_dim, dim=1)
        # return mu, logvar

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)  # Convert logvar to std
        eps = torch.randn_like(std)  # Sample epsilon ~ N(0,1)
        return mu + eps * std  # Reparameterization trick

    def decode(self, z):
        x = self.fc_decoder(z).view(-1, 64, self.last_size, self.last_size)
        return self.decoder(x)

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        return self.decode(z), mu, logvar

# ✅ 2️⃣ Hàm tính Loss (Reconstruction Loss + KL Divergence)
def vae_loss(x_recon, x, mu, logvar):
    # recon_loss = F.binary_cross_entropy(x_recon, x, reduction="sum")  # Reconstruction loss
    recon_loss = F.mse_loss(x_recon, x, reduction="sum")  # Reconstruction loss
    kl_div = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())  # KL Divergence
    return recon_loss + kl_div

if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ConvVAE(latent_dim=256, input_size=128)

    # Load state_dict
    model.load_state_dict(torch.load("res/model/VAE/gray_model_128.pth", map_location=device))
    # Chuyển sang chế độ eval để inference
    print(model.eval())
