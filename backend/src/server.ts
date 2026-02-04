import App from './app';

// Handle uncaught exceptions
process.on('uncaughtException', (error: Error) => {
  console.error('❌ Uncaught Exception:', error);
  process.exit(1);
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason: any, promise: Promise<any>) => {
  console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
  process.exit(1);
});

// Graceful shutdown
const gracefulShutdown = async (app: App, signal: string) => {
  console.log(`\n📡 Received ${signal}. Graceful shutdown...`);
  try {
    await app.stop();
    console.log('✅ Server shut down gracefully');
    process.exit(0);
  } catch (error) {
    console.error('❌ Error during shutdown:', error);
    process.exit(1);
  }
};

// Start the application
const startServer = async () => {
  try {
    const app = new App();
    
    // Register shutdown handlers
    process.on('SIGTERM', () => gracefulShutdown(app, 'SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown(app, 'SIGINT'));
    
    await app.start();
  } catch (error) {
    console.error('❌ Failed to start application:', error);
    process.exit(1);
  }
};

startServer();