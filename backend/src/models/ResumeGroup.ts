import mongoose, { Document, Schema } from 'mongoose';

export interface IResumeGroup extends Document {
  name: string;
  source: 'upload' | 'email' | 'api';
  resume_count: number;
  createdAt: Date;
  updatedAt: Date;
}

const resumeGroupSchema = new Schema<IResumeGroup>({
  name: {
    type: String,
    required: true,
    trim: true
  },
  source: {
    type: String,
    enum: ['upload', 'email', 'api'],
    default: 'upload'
  },
  resume_count: {
    type: Number,
    default: 0
  }
}, {
  timestamps: true
});

export default mongoose.model<IResumeGroup>('ResumeGroup', resumeGroupSchema);