import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models

class ResNetEncoder(nn.Module):
    def __init__(self, latent_dim=32, input_size=64):
        super().__init__()
        self.input_size = input_size
        self.latent_dim = latent_dim

        resnet = models.resnet18(pretrained=True)
        self.feature_extractor = nn.Sequential(*list(resnet.children())[:-1])  # Bỏ fc layer cuối
        self.fc_mu = nn.Linear(resnet.fc.in_features, latent_dim)
        self.fc_logvar = nn.Linear(resnet.fc.in_features, latent_dim)

    def forward(self, x):
        x = self.feature_extractor(x)
        x = torch.flatten(x, start_dim=1)  # Reshape thành (batch, features)
        mu = self.fc_mu(x)
        logvar = self.fc_logvar(x)
        return mu, logvar

class ResNetDecoder(nn.Module):
    def __init__(self, latent_dim=32, input_size=64):
        super().__init__()
        self.input_size = input_size
        self.latent_dim = latent_dim

        start_size = input_size // 32
        self.fc = nn.Linear(latent_dim, 512 * start_size * start_size)  # Map latent_dim thành feature map nhỏ
        self.deconv_layers = nn.Sequential(
            nn.ConvTranspose2d(512, 256, 3, stride=2, padding=1, output_padding=1), #4x4
            nn.ReLU(),
            nn.ConvTranspose2d(256, 128, 3, stride=2, padding=1, output_padding=1), #8x8
            nn.ReLU(),
            nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1), #16x16
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1), #32x32
            nn.ReLU(),
            nn.ConvTranspose2d(32, 3, 3, stride=2, padding=1, output_padding=1), #64x64
            nn.Sigmoid(),  # Output ảnh 3 kênh, giá trị [0,1]
        )

    def forward(self, z):
        start_size = self.input_size // 32
        x = self.fc(z)
        x = x.view(-1, 512, start_size, start_size)  # Reshape thành feature map 2x2
        x = self.deconv_layers(x)
        return x

class ResnetVAE(nn.Module):
    def __init__(self, latent_dim=32, input_size=64):
        super().__init__()
        self.input_size = input_size
        self.latent_dim = latent_dim

        self.encoder = ResNetEncoder(latent_dim, input_size)
        self.decoder = ResNetDecoder(latent_dim, input_size)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        mu, logvar = self.encoder(x)
        z = self.reparameterize(mu, logvar)
        recon_x = self.decoder(z)
        return recon_x, mu, logvar


# ✅ 2️⃣ Hàm tính Loss (Reconstruction Loss + KL Divergence)
def vae_loss(x_recon, x, mu, logvar):
    # recon_loss = F.binary_cross_entropy(x_recon, x, reduction="sum")  # Reconstruction loss
    recon_loss = F.mse_loss(x_recon, x, reduction="sum")  # Reconstruction loss
    kl_div = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())  # KL Divergence
    # print(f"    Recon loss: {recon_loss / len(x_recon)}, KL div: {kl_div / len(x_recon)}")
    return recon_loss + kl_div