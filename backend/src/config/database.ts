import mongoose from 'mongoose';
import dotenv from 'dotenv';

dotenv.config();

interface DatabaseConfig {
  uri: string;
  options: mongoose.ConnectOptions;
}

const config: DatabaseConfig = {
  uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/kreeda_hiring_bot',
  options: {
    // Connection options
  }
};

class Database {
  private static instance: Database;
  private isConnected: boolean = false;

  private constructor() {}

  public static getInstance(): Database {
    if (!Database.instance) {
      Database.instance = new Database();
    }
    return Database.instance;
  }

  public async connect(): Promise<void> {
    if (this.isConnected) {
      console.log('✅ Database already connected');
      return;
    }

    try {
      await mongoose.connect(config.uri, config.options);
      this.isConnected = true;
      console.log('✅ Connected to MongoDB successfully');

      // Handle connection events
      mongoose.connection.on('disconnected', () => {
        console.log('❌ MongoDB disconnected');
        this.isConnected = false;
      });

      mongoose.connection.on('error', (error) => {
        console.error('❌ MongoDB connection error:', error);
        this.isConnected = false;
      });

    } catch (error) {
      console.error('❌ Failed to connect to MongoDB:', error);
      process.exit(1);
    }
  }

  public async disconnect(): Promise<void> {
    if (!this.isConnected) {
      return;
    }

    try {
      await mongoose.disconnect();
      this.isConnected = false;
      console.log('✅ Disconnected from MongoDB');
    } catch (error) {
      console.error('❌ Error disconnecting from MongoDB:', error);
    }
  }

  public getConnectionStatus(): boolean {
    return this.isConnected;
  }
}

export default Database;