#!/bin/bash
# Production Deployment Script for Kreeda Hiring Bot

set -e  # Exit on any error

echo "🚀 Kreeda Hiring Bot - Production Deployment"
echo "=============================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo ""
    echo "📝 Please create .env file with:"
    echo "   1. Copy .env.production.template to .env"
    echo "   2. Update NEXT_PUBLIC_BASE_URL with your Tailscale URL"
    echo "   3. Update OPENAI_API_KEY with your API key"
    echo ""
    exit 1
fi

# Check if NEXT_PUBLIC_BASE_URL is set
if ! grep -q "NEXT_PUBLIC_BASE_URL=" .env; then
    echo "⚠️  Warning: NEXT_PUBLIC_BASE_URL not found in .env"
    echo "   File proxy may not work correctly!"
fi

# Check if OPENAI_API_KEY is set
if ! grep -q "OPENAI_API_KEY=" .env; then
    echo "❌ Error: OPENAI_API_KEY not found in .env"
    echo "   Worker will not be able to process resumes!"
    exit 1
fi

echo "✅ Environment file found"
echo ""

# Pull latest images
echo "📦 Pulling latest Docker images..."
docker compose pull

echo ""
echo "🔨 Building containers..."
docker compose build --no-cache

echo ""
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 10

echo ""
echo "📊 Service Status:"
docker compose ps

echo ""
echo "=============================================="
echo "✅ Deployment Complete!"
echo ""
echo "📝 Next Steps:"
echo "   1. Setup Tailscale tunnel:"
echo "      tailscale serve https / http://localhost:3000"
echo ""
echo "   2. Get your Tailscale URL and update .env if needed"
echo ""
echo "   3. Restart Next.js if you changed .env:"
echo "      docker compose restart nextjs"
echo ""
echo "   4. View logs:"
echo "      docker compose logs -f"
echo ""
echo "🌐 Your app will be available at:"
grep "NEXT_PUBLIC_BASE_URL=" .env | cut -d'=' -f2
echo ""
