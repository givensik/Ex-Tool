# Webhook Server

이 프로젝트는 웹훅 수신자 역할을 하는 Next.js 애플리케이션입니다. 로컬 서버를 인터넷에 자동으로 노출시키기 위해 Cloudflare Tunnel을 시작하는 커스텀 서버(`server.js`)를 포함하고 있습니다.

## requirements

- Node.js (v18 이상 권장)
- npm 또는 yarn

## 설치

```bash
npm install
# 또는
yarn install
```

## 사용법

### Development

개발 서버를 시작하려면 다음 명령어를 실행하세요:

```bash
npm run dev
# 또는
yarn dev
```

이 명령어는 다음 작업을 수행합니다:
1. `http://localhost:3000`에서 Next.js 서버를 시작합니다.
2. Cloudflare Tunnel을 시작합니다.
3. 콘솔에 공개 URL (예: `https://<random-id>.trycloudflare.com`)을 출력합니다.

### Production

프로덕션 서버를 빌드하고 시작하려면 다음 명령어를 실행하세요:

```bash
npm run build
npm start
# 또는
yarn build
yarn start
```

## scripts

- `dev`: `node server.js` 실행 (개발 모드)
- `build`: `next build` 실행 (애플리케이션 빌드)
- `start`: `node server.js` 실행 (프로덕션 모드)
- `lint`: `next lint` 실행 (코드 린트)

## features

- **Cloudflare Tunnel 통합**: `cloudflared`를 사용하여 로컬 서버를 자동으로 인터넷에 노출합니다.
- **커스텀 서버**: 요청을 처리하고 터널 프로세스를 관리하기 위해 커스텀 Node.js 서버를 사용합니다.
