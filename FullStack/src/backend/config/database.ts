import mongoose from 'mongoose';

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/hrbot_hiring';

let isConnected = false;

export async function connectToDatabase() {
  if (isConnected) {
    return mongoose.connection;
  }

  await mongoose.connect(MONGODB_URI);
  isConnected = true;
  return mongoose.connection;
}

export default mongoose;
