/**
 * 循环导入文件 A
 */

import { CircularB } from './CircularB';

export class CircularA {
    useB() {
        return new CircularB();
    }
}
