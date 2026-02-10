import asyncio
from bullmq import Queue

async def main():
    # Clear default queue
    q_default = Queue('default', {
        'connection': {
            'host': 'redis',
            'port': 6379,
            'password': 'password123'
        }
    })
    await q_default.drain()
    print('Drained default queue')
    
    # Clear resume-processing queue
    q_resume = Queue('resume-processing', {
        'connection': {
            'host': 'redis',
            'port': 6379,
            'password': 'password123'
        }
    })
    await q_resume.drain()
    print('Drained resume-processing queue')

if __name__ == '__main__':
    asyncio.run(main())
